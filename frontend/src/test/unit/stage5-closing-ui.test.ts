import {
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rm,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";

import { parseManifest } from "@/schemas/dataset.schema";
import { parseStage5Manifest, parseStage5Summaries } from "@/schemas/stage5-preview.schema";
import { PreviewApiDataSource } from "@/services/preview-api-data-source";
import { createPreviewRouteHandler } from "@/server/pathos-preview";

const BUNDLE_ROOT = process.env.PATHOS_PREVIEW_BUNDLE_DIR
  ? path.resolve(process.env.PATHOS_PREVIEW_BUNDLE_DIR)
  : path.resolve(process.cwd(), "data/preview");

async function artifact<T = unknown>(name: string): Promise<T> {
  return JSON.parse(await readFile(path.join(BUNDLE_ROOT, name), "utf8")) as T;
}

function backendEnv(bundleDir = BUNDLE_ROOT) {
  return {
    NODE_ENV: "test",
    PATHOS_DATA_MODE: "backend",
    PATHOS_PREVIEW_BUNDLE_DIR: bundleDir,
  } as NodeJS.ProcessEnv;
}

describe("Stage 5 closing UI compliance", () => {
  it("01 retains backend feature readiness in the frontend manifest", async () => {
    const manifest = parseManifest(await artifact("manifest.json"));
    expect(manifest.disabledFeatures).toContain("parent_mode");
    expect(manifest.enabledFeatures).toContain("student_mode");
  });

  it("02 backend parent readiness false makes parent unavailable", async () => {
    const policy = await import("@/hooks/use-view-state-bridge");
    const manifest = parseManifest(await artifact("manifest.json"));
    expect(typeof (policy as any).isParentModeAvailable).toBe("function");
    expect((policy as any).isParentModeAvailable(manifest)).toBe(false);
  });

  it("03 fixture readiness without a parent disable remains available", async () => {
    const policy = await import("@/hooks/use-view-state-bridge");
    const response = await createPreviewRouteHandler({
      NODE_ENV: "test",
      PATHOS_DATA_MODE: "fixture",
    } as NodeJS.ProcessEnv)(
      new Request("http://localhost/api/pathos/preview?endpoint=manifest"),
    );
    const fixtureManifest = parseManifest(await response.json());
    expect((policy as any).isParentModeAvailable(fixtureManifest)).toBe(true);
  });

  it("04 persisted parent state safely degrades while student remains enabled", async () => {
    const policy = await import("@/hooks/use-view-state-bridge");
    expect(typeof (policy as any).resolveAllowedViewMode).toBe("function");
    expect((policy as any).resolveAllowedViewMode("parent", false)).toBe("student");
    expect((policy as any).resolveAllowedViewMode("student", false)).toBe("student");
    expect((policy as any).resolveAllowedViewMode("parent", true)).toBe("parent");
  });

  it.each([
    ["TIMEOUT", "unavailable", true],
    ["BACKEND_UNAVAILABLE", "unavailable", true],
    ["UNIVERSITY_NOT_FOUND", "not_found", false],
    ["BUNDLE_SCHEMA_INVALID", "invalid_contract", false],
    ["UNSUPPORTED_CONTRACT_VERSION", "invalid_contract", false],
    ["FEATURE_DISABLED", "feature_disabled", false],
  ])(
    "05 classifies %s as a safe %s presentation",
    async (code, expectedKind, retryable) => {
      const states = await import("@/components/shared/data-states");
      expect(typeof (states as any).getPreviewErrorPresentation).toBe("function");
      expect((states as any).getPreviewErrorPresentation(code)).toMatchObject({
        kind: expectedKind,
        retryable,
      });
    },
  );

  it("06 preserves university-not-found BFF code without fixture fallback", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: "preview_backend_error",
            code: "UNIVERSITY_NOT_FOUND",
            message: "internal detail omitted",
            retryable: false,
          },
          { status: 404 },
        ),
      ),
    );
    await expect(
      new PreviewApiDataSource().getUniversityDetail("candidate-v2:missing"),
    ).rejects.toMatchObject({ code: "UNIVERSITY_NOT_FOUND" });
    vi.unstubAllGlobals();
  });

  it("07 supports backend recovery after a retry", async () => {
    const manifest = await artifact("manifest.json");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json(
          { code: "BACKEND_UNAVAILABLE", retryable: true },
          { status: 503 },
        ),
      )
      .mockResolvedValueOnce(Response.json(manifest));
    vi.stubGlobal("fetch", fetchMock);
    const source = new PreviewApiDataSource();
    await expect(source.getManifest()).rejects.toMatchObject({
      code: "BACKEND_UNAVAILABLE",
    });
    await expect(source.getManifest()).resolves.toMatchObject({
      counts: { universities: 62 },
    });
    vi.unstubAllGlobals();
  });

  it("08 uses dynamic university routing with no fixture static params", async () => {
    const route = await import("@/app/university/[id]/page");
    const source = await readFile(
      path.join(process.cwd(), "src/app/university/[id]/page.tsx"),
      "utf8",
    );
    expect((route as any).dynamic).toBe("force-dynamic");
    expect((route as any).generateStaticParams).toBeUndefined();
    expect(source).not.toMatch(/fixture|generateStaticParams/);
  });

  it("09 real backend Bundle has 62 unique stable route IDs", async () => {
    const rows = parseStage5Summaries(await artifact("universities.json"));
    expect(rows).toHaveLength(62);
    expect(new Set(rows.map(({ id }) => id)).size).toBe(62);
  });

  it("10 missing Bundle fails closed", async () => {
    const response = await createPreviewRouteHandler(
      backendEnv("/definitely/missing"),
    )(new Request("http://localhost/api/pathos/preview?endpoint=manifest"));
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({
      code: "BUNDLE_ARTIFACT_MISSING",
    });
  });

  it("11 unsupported contract version fails closed", async () => {
    const manifest = await artifact<object>("manifest.json");
    expect(() =>
      parseStage5Manifest({
        ...manifest,
        contractVersion: "unsupported",
      }),
    ).toThrow(/contractVersion/);
  });

  it("12 normal backend university detail remains available", async () => {
    const response = await createPreviewRouteHandler(backendEnv())(
      new Request(
        "http://localhost/api/pathos/preview?endpoint=university&id=candidate-v2%3Aharvard-university",
      ),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      id: "candidate-v2:harvard-university",
    });
  });

  it("13 missing source index is a Bundle failure, not university 404", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "pathos-closing-ui-"));
    try {
      await mkdir(path.join(root, "university-details"), { recursive: true });
      await copyFile(
        path.join(BUNDLE_ROOT, "manifest.json"),
        path.join(root, "manifest.json"),
      );
      await copyFile(
        path.join(
          BUNDLE_ROOT,
          "university-details/candidate-v2:harvard-university.json",
        ),
        path.join(
          root,
          "university-details/candidate-v2:harvard-university.json",
        ),
      );
      const response = await createPreviewRouteHandler(backendEnv(root))(
        new Request(
          "http://localhost/api/pathos/preview?endpoint=university&id=candidate-v2%3Aharvard-university",
        ),
      );
      expect(response.status).toBe(503);
      expect(await response.json()).toMatchObject({
        code: "BUNDLE_ARTIFACT_MISSING",
      });
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
