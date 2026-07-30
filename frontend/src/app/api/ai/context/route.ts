// AI context BFF route — POST /api/ai/context
// See `@/server/ai-context.ts` for the data assembly logic.
//
// We deliberately do NOT export `dynamic = "force-dynamic"` here.
// The repository is configured with `output: "export"`, which is
// incompatible with that directive — Next.js throws 500 in dev and
// fails `next build`. Route Handlers always run per-request in dev
// regardless; the directive is only meaningful at build time, and at
// build time the entire `/api/*` surface gets pruned anyway.

import { handleAiContextRoute } from "@/server/ai-context";

export async function POST(req: Request): Promise<Response> {
  return handleAiContextRoute(req);
}
