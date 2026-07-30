import type { NextResponse } from "next/server";

import {
  handleFixturePreviewRoute,
  loadUniversities,
} from "@/server/fixture-preview";
import { handleBackendPreviewRoute, previewErrorResponse } from "@/server/backend-preview";

export type PathosDataMode = "fixture" | "backend";

export function resolveDataMode(env: NodeJS.ProcessEnv = process.env): PathosDataMode {
  const requested = env.PATHOS_DATA_MODE?.trim();
  if (requested === "fixture") {
    if (env.NODE_ENV === "production") {
      throw new Error("PATHOS_DATA_MODE=fixture is prohibited in production");
    }
    return "fixture";
  }
  if (!requested || requested === "backend") return "backend";
  throw new Error(`Unsupported PATHOS_DATA_MODE: ${requested}`);
}

export function createPreviewRouteHandler(
  env: NodeJS.ProcessEnv = process.env,
): (req: Request) => Promise<NextResponse> {
  return async (req: Request) => {
    let mode: PathosDataMode;
    try {
      mode = resolveDataMode(env);
    } catch (error) {
      return previewErrorResponse(error, "mode-selection");
    }
    if (mode === "fixture") return handleFixturePreviewRoute(req);
    return handleBackendPreviewRoute(req, env);
  };
}

export const handlePreviewRoute = createPreviewRouteHandler();

// Fixture-only compatibility for legacy AI code. Backend mode AI routes
// are disabled before this function is called.
export { loadUniversities };
