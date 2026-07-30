-- PathOS canonical university database: stable identity, selection and provenance.
-- PostgreSQL / Supabase compatible. No extensions or remote services required.

CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  publisher TEXT NOT NULL,
  page_title TEXT NOT NULL,
  source_type TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  accessed_at TIMESTAMPTZ NOT NULL,
  academic_year TEXT,
  ranking_edition TEXT,
  content_hash TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'archived', 'incomplete', 'test_only')),
  evidence_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE universities (
  internal_id TEXT PRIMARY KEY,
  unitid TEXT UNIQUE,
  college_scorecard_id TEXT UNIQUE,
  official_name TEXT NOT NULL,
  name_zh TEXT,
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb,
  official_website TEXT,
  institution_type TEXT,
  control_type TEXT,
  main_campus_address TEXT,
  city TEXT NOT NULL,
  county TEXT,
  state TEXT NOT NULL,
  state_code CHAR(2) NOT NULL,
  census_region TEXT,
  census_division TEXT,
  latitude NUMERIC(9, 6),
  longitude NUMERIC(9, 6),
  selection_reason TEXT NOT NULL CHECK (selection_reason IN ('national_top_50', 'program_top_20', 'both')),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  last_verified_at TIMESTAMPTZ,
  CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180)
);

CREATE TABLE university_sources (
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  relation_type TEXT NOT NULL CHECK (relation_type IN ('identity', 'location', 'official_website', 'alias')),
  PRIMARY KEY (university_id, source_id, relation_type)
);

CREATE TABLE university_selection_memberships (
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  selection_reason TEXT NOT NULL CHECK (selection_reason IN ('national_top_50', 'program_top_20')),
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  selected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (university_id, selection_reason, source_id)
);

CREATE TABLE university_facts (
  fact_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  field_name TEXT NOT NULL,
  value_json JSONB NOT NULL,
  value_type TEXT NOT NULL CHECK (value_type IN ('number', 'string', 'boolean', 'array', 'object', 'null')),
  academic_year TEXT,
  verified_at TIMESTAMPTZ NOT NULL,
  null_reason TEXT,
  CHECK ((value_type = 'null') = (null_reason IS NOT NULL)),
  UNIQUE (university_id, field_name, academic_year)
);

CREATE TABLE university_fact_sources (
  fact_id TEXT NOT NULL REFERENCES university_facts(fact_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (fact_id, source_id)
);

CREATE INDEX universities_state_code_idx ON universities(state_code);
CREATE INDEX university_facts_field_name_idx ON university_facts(field_name);
