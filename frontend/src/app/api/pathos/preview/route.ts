// Single Next.js Route Handler that dispatches to pathos-preview.ts.
// Using one entry point keeps the route table flat and respects the
// "Browser → /api/pathos/* → backend preview API" topology from the
// PathOS architecture spec.
//
// We deliberately do NOT export `dynamic = "force-dynamic"`. The
// repository is configured with `output: "export"`, which is
// incompatible with that directive and causes 500s in dev. Route
// Handlers always run per-request in dev regardless.

import { NextResponse } from "next/server";
import { handlePreviewRoute } from "@/server/pathos-preview";

export async function GET(req: Request) {
  return handlePreviewRoute(req);
}
