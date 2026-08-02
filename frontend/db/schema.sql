-- PathOS Preview schema for Supabase (PostgreSQL 15+).
-- Run once in Supabase SQL Editor, or via `npm run db:reset`.
-- Safe to re-run: every CREATE uses IF NOT EXISTS.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Universities: 1 row per school. Top-level scalars are extracted to
-- columns for filter / index. Everything else stays in `payload` JSONB.
CREATE TABLE IF NOT EXISTS universities (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  chinese_name    TEXT,
  city            TEXT,
  state           TEXT,
  region          TEXT,
  school_type     TEXT,
  ranking_band    TEXT,
  ranking_tier    TEXT,
  national_ranking INTEGER,
  latitude        DOUBLE PRECISION,
  longitude       DOUBLE PRECISION,
  display_tier    TEXT,
  source_status   TEXT,
  source_commit   TEXT,
  dataset_version TEXT,
  preview_only    BOOLEAN NOT NULL DEFAULT TRUE,
  payload         JSONB NOT NULL,
  search_text     TSVECTOR,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_universities_state ON universities(state);
CREATE INDEX IF NOT EXISTS idx_universities_tier  ON universities(ranking_tier);
CREATE INDEX IF NOT EXISTS idx_universities_geo   ON universities(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_universities_fts   ON universities USING GIN(search_text);
CREATE INDEX IF NOT EXISTS idx_universities_trgm  ON universities USING GIN(name gin_trgm_ops, chinese_name gin_trgm_ops);

-- University detail: 1 row per school, large JSONB blob.
CREATE TABLE IF NOT EXISTS university_details (
  university_id  TEXT PRIMARY KEY REFERENCES universities(id) ON DELETE CASCADE,
  payload        JSONB NOT NULL,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Region metrics envelope: stored as one JSONB blob because the current
-- preview is `status=blocked, records=[]`. When choropleth is enabled,
-- add a separate region_metric_records table here.
CREATE TABLE IF NOT EXISTS region_envelope (
  id          INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  payload     JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Status dictionary: keyed by code, payload holds icon/label/tone.
CREATE TABLE IF NOT EXISTS status_dictionary (
  code        TEXT PRIMARY KEY,
  payload     JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Source index: array of source references. Single row.
CREATE TABLE IF NOT EXISTS source_index (
  id          INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  payload     JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Manifest: dataset metadata + hash table. Single row.
CREATE TABLE IF NOT EXISTS manifest (
  id          INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  payload     JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
