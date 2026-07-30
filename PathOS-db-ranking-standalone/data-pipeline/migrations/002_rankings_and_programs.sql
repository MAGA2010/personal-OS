-- Rankings are immutable snapshots. Undergraduate and graduate families stay distinct.

CREATE TABLE ranking_snapshots (
  ranking_snapshot_id TEXT PRIMARY KEY,
  ranking_system TEXT NOT NULL,
  ranking_family TEXT NOT NULL CHECK (ranking_family IN ('national_universities', 'undergraduate_program', 'graduate_program', 'global_universities')),
  category TEXT NOT NULL,
  edition TEXT NOT NULL,
  publication_date DATE,
  snapshot_date DATE NOT NULL,
  source_id TEXT REFERENCES sources(source_id),
  included_in_pathos_scope BOOLEAN NOT NULL DEFAULT FALSE,
  exclusion_reason TEXT,
  UNIQUE (ranking_system, ranking_family, category, edition)
);

CREATE TABLE ranking_snapshot_sources (
  ranking_snapshot_id TEXT NOT NULL REFERENCES ranking_snapshots(ranking_snapshot_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (ranking_snapshot_id, source_id)
);

CREATE TABLE programs (
  program_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL UNIQUE,
  display_name_zh TEXT,
  cip_code_2digit CHAR(2),
  cip_code_4digit CHAR(4),
  cip_code_6digit CHAR(6),
  degree_level TEXT NOT NULL CHECK (degree_level IN ('undergraduate', 'graduate', 'other')),
  aliases JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE university_programs (
  university_program_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  program_id TEXT REFERENCES programs(program_id),
  official_program_name TEXT NOT NULL,
  school_or_college TEXT,
  department TEXT,
  degree_type TEXT,
  undergraduate_available BOOLEAN NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  source_id TEXT REFERENCES sources(source_id),
  academic_year TEXT NOT NULL,
  cip_mapping_status TEXT NOT NULL CHECK (cip_mapping_status IN ('mapped', 'unresolved', 'not_applicable')),
  UNIQUE (university_id, official_program_name, degree_type, academic_year)
);

CREATE TABLE university_rankings (
  university_ranking_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  ranking_snapshot_id TEXT NOT NULL REFERENCES ranking_snapshots(ranking_snapshot_id) ON DELETE CASCADE,
  numeric_rank INTEGER NOT NULL CHECK (numeric_rank >= 1),
  displayed_rank TEXT NOT NULL,
  tied BOOLEAN NOT NULL DEFAULT FALSE,
  tier TEXT,
  source_id TEXT REFERENCES sources(source_id),
  verified_at TIMESTAMPTZ NOT NULL,
  UNIQUE (university_id, ranking_snapshot_id)
);

CREATE TABLE university_ranking_sources (
  university_ranking_id TEXT NOT NULL REFERENCES university_rankings(university_ranking_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (university_ranking_id, source_id)
);

CREATE TABLE program_rankings (
  program_ranking_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  program_id TEXT REFERENCES programs(program_id),
  ranking_snapshot_id TEXT NOT NULL REFERENCES ranking_snapshots(ranking_snapshot_id) ON DELETE CASCADE,
  ranking_category TEXT NOT NULL,
  numeric_rank INTEGER NOT NULL CHECK (numeric_rank >= 1),
  displayed_rank TEXT NOT NULL,
  tied BOOLEAN NOT NULL DEFAULT FALSE,
  source_id TEXT REFERENCES sources(source_id),
  UNIQUE (university_id, program_id, ranking_snapshot_id, ranking_category)
);

CREATE TABLE program_ranking_sources (
  program_ranking_id TEXT NOT NULL REFERENCES program_rankings(program_ranking_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (program_ranking_id, source_id)
);

CREATE TABLE tuition_records (
  tuition_record_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  program_id TEXT REFERENCES programs(program_id),
  school_or_college TEXT,
  academic_year TEXT NOT NULL,
  degree_level TEXT NOT NULL CHECK (degree_level IN ('undergraduate', 'graduate', 'other')),
  residency_basis TEXT NOT NULL,
  currency CHAR(3) NOT NULL,
  tuition_amount NUMERIC(14, 2),
  mandatory_fees NUMERIC(14, 2),
  comparable_annual_total NUMERIC(14, 2),
  pricing_basis TEXT NOT NULL CHECK (pricing_basis IN ('university_wide', 'school_or_college', 'program_specific', 'per_credit', 'not_public', 'not_applicable')),
  source_id TEXT REFERENCES sources(source_id),
  verified_at TIMESTAMPTZ NOT NULL,
  notes TEXT,
  CHECK (tuition_amount IS NULL OR tuition_amount >= 0),
  CHECK (mandatory_fees IS NULL OR mandatory_fees >= 0),
  CHECK (comparable_annual_total IS NULL OR comparable_annual_total >= 0)
);

CREATE TABLE student_faculty_ratio_records (
  ratio_record_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  ratio_value NUMERIC(8, 3),
  ratio_display TEXT,
  academic_year TEXT NOT NULL,
  definition TEXT NOT NULL,
  source_id TEXT REFERENCES sources(source_id),
  verified_at TIMESTAMPTZ NOT NULL,
  null_reason TEXT,
  CHECK ((ratio_value IS NULL) = (null_reason IS NOT NULL))
);

CREATE INDEX university_rankings_snapshot_idx ON university_rankings(ranking_snapshot_id, numeric_rank);
CREATE INDEX program_rankings_snapshot_idx ON program_rankings(ranking_snapshot_id, numeric_rank);
CREATE INDEX university_programs_university_idx ON university_programs(university_id, undergraduate_available, active);
