import { Pool, type PoolClient } from "pg";

let _pool: Pool | null = null;

export function getPool(): Pool {
  if (_pool) return _pool;
  const connStr = process.env.DATABASE_URL;
  if (!connStr) throw new DatabaseNotConfiguredError();
  _pool = new Pool({
    connectionString: connStr,
    ssl: connStr.includes("supabase") || connStr.includes("sslmode=require")
      ? { rejectUnauthorized: false }
      : undefined,
    max: Number(process.env.PATHOS_DB_POOL_MAX ?? 10),
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 5_000,
  });
  _pool.on("error", (err) => { console.error("[pathos db] pool error:", err); });
  return _pool;
}

export async function withClient<T>(fn: (c: PoolClient) => Promise<T>): Promise<T> {
  const client = await getPool().connect();
  try { return await fn(client); } finally { client.release(); }
}

export class DatabaseNotConfiguredError extends Error {
  readonly code = "DATABASE_NOT_CONFIGURED";
  readonly status = 503;
  readonly retryable = false;
  readonly featureStatus = "unavailable";
  constructor() {
    super("DATABASE_URL is not configured. Set it in environment variables.");
    this.name = "DatabaseNotConfiguredError";
  }
}
