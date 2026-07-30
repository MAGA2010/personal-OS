"use client";

// AiContextPanel — calls POST /api/ai/context and renders the 5 preset
// questions. Each question is wired to forward to the analyze endpoint.
//
// Behaviour:
//   - When the backend is offline (503), the panel renders an
//     explicit "数据补充中" banner rather than a fake answer.
//   - The 5 preset questions are audience-tagged so the user sees ones
//     appropriate to their current viewMode.
//   - Click on a preset sends { schools: ids, question } to
//     /api/ai/analyze in `school_assessment` mode.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bot, RefreshCw, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

export interface AiContextPanelProps {
  schoolIds: string[];
  viewMode: "parent" | "student";
  activeMetricId?: string;
  selectedRegionFips?: string;
}

interface AiContextPayload {
  viewMode: "parent" | "student";
  generatedAt: string;
  schools: Array<{ id: string; chineseName: string; name: string }>;
  presetQuestions: ReadonlyArray<{ id: string; text: string; audience: "parent" | "student" | "both" }>;
}

type FetchState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; payload: AiContextPayload }
  | { status: "error"; message: string; code?: string };

export function AiContextPanel({
  schoolIds,
  viewMode,
  activeMetricId,
  selectedRegionFips,
}: AiContextPanelProps) {
  const idsKey = useMemo(() => schoolIds.slice(0, 3).join(","), [schoolIds]);
  const [state, setState] = useState<FetchState>({ status: "idle" });
  const router = useRouter();

  const reload = useCallback(async () => {
    if (!schoolIds.length) {
      setState({ status: "idle" });
      return;
    }
    setState({ status: "loading" });
    try {
      const resp = await fetch("/api/ai/context", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          schoolIds: schoolIds.slice(0, 3),
          viewMode,
          activeMetricId,
          selectedRegionFips,
        }),
      });
      if (resp.status === 503) {
        setState({
          status: "error",
          message: "数据补充中 — 后端预览接口尚未上线",
          code: "PREVIEW_NOT_YET_AVAILABLE",
        });
        return;
      }
      if (!resp.ok) {
        setState({ status: "error", message: `HTTP ${resp.status}` });
        return;
      }
      const payload = (await resp.json()) as AiContextPayload;
      setState({ status: "ready", payload });
    } catch (e) {
      setState({ status: "error", message: (e as Error).message });
    }
  }, [schoolIds, viewMode, activeMetricId, selectedRegionFips]);

  useEffect(() => {
    void reload();
  }, [reload, idsKey]);

  const visible = useMemo(() => {
    if (state.status !== "ready") return [];
    return state.payload.presetQuestions.filter(
      (q) => q.audience === viewMode || q.audience === "both",
    );
  }, [state, viewMode]);

  const askPreset = useCallback(
    (q: { id: string; text: string }) => {
      // Forward to existing analyze endpoint via querystring; the page
      // can decode it and prefill the textarea.
      const params = new URLSearchParams({
        mode: "school_assessment",
        questionId: q.id,
        q: q.text,
        schools: schoolIds.slice(0, 3).join(","),
      });
      router.push(`/ai/analyze?${params.toString()}`);
    },
    [router, schoolIds],
  );

  if (schoolIds.length === 0) {
    return (
      <aside className="rounded-xl border border-dashed border-line bg-panel/60 p-4 text-xs text-ink/52">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-ink/40" aria-hidden="true" />
          <span>添加学校到比较即可解锁 AI 助理建议。</span>
        </div>
      </aside>
    );
  }

  return (
    <aside className="rounded-xl border border-line bg-panel p-4 text-xs">
      <header className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-medium text-ink">
          <Sparkles size={13} className="text-cobalt" aria-hidden="true" />
          <span>AI 助理</span>
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          className="grid h-6 w-6 place-items-center rounded text-ink/40 hover:bg-line/30"
          aria-label="刷新 AI 上下文"
        >
          <RefreshCw size={12} />
        </button>
      </header>

      {state.status === "loading" && (
        <p className="text-ink/52">正在加载上下文…</p>
      )}

      {state.status === "error" && (
        <div className="rounded-md border border-persimmon/30 bg-persimmon/10 px-3 py-2 text-persimmon/80">
          <p className="font-medium">数据补充中</p>
          <p className="mt-0.5 text-[11px] opacity-80">{state.message}</p>
        </div>
      )}

      {state.status === "ready" && (
        <>
          <p className="mb-2 text-ink/44">
            基于当前 {state.payload.schools.length} 所学校:
            {state.payload.schools.map((s) => s.chineseName).join(" · ")}
          </p>
          <ul className="space-y-1">
            {visible.map((q) => (
              <li key={q.id}>
                <button
                  type="button"
                  onClick={() => askPreset(q)}
                  className="w-full rounded-md border border-line/60 bg-white/70 px-3 py-2 text-left text-[11px] text-ink/72 transition-colors hover:border-cobalt/40 hover:bg-cobalt/5"
                >
                  {q.text}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}

export default AiContextPanel;
