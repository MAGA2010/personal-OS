"use client";

// Data source context.
// All components MUST consume the data source from `useDataSource()`.
// This keeps the implementation swappable (preview api / unavailable / future production).

import { createContext, useContext, type ReactNode } from "react";
import type { PathOSDataSource } from "@/services/pathos-data-source";
import { PreviewApiDataSource } from "@/services/preview-api-data-source";

const DataSourceContext = createContext<PathOSDataSource | null>(null);

export function DataSourceProvider({
  children,
  source,
}: {
  children: ReactNode;
  source?: PathOSDataSource;
}) {
  const effective = source ?? new PreviewApiDataSource(
    process.env.NEXT_PUBLIC_PATHOS_API_BASE_URL ?? "/api/pathos/preview",
  );
  return (
    <DataSourceContext.Provider value={effective}>{children}</DataSourceContext.Provider>
  );
}

export function useDataSource(): PathOSDataSource | null {
  return useContext(DataSourceContext);
}
