-- Enrichment data is optional. Absence is represented explicitly, never guessed.

CREATE TABLE nearby_places (
  nearby_place_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  place_name TEXT NOT NULL,
  state_code CHAR(2) NOT NULL,
  census_place_id TEXT,
  latitude NUMERIC(9, 6) NOT NULL,
  longitude NUMERIC(9, 6) NOT NULL,
  distance_km NUMERIC(10, 3) NOT NULL CHECK (distance_km >= 0),
  distance_method TEXT NOT NULL CHECK (distance_method IN ('haversine')),
  rank_by_distance SMALLINT NOT NULL CHECK (rank_by_distance >= 1),
  source_id TEXT REFERENCES sources(source_id),
  UNIQUE (university_id, rank_by_distance),
  UNIQUE (university_id, census_place_id)
);

CREATE TABLE distinguished_students (
  distinguished_student_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  program_id TEXT REFERENCES programs(program_id),
  person_name TEXT,
  achievement TEXT,
  student_status TEXT,
  null_reason TEXT,
  CHECK ((person_name IS NULL) = (null_reason IS NOT NULL))
);

CREATE TABLE distinguished_student_sources (
  distinguished_student_id TEXT NOT NULL REFERENCES distinguished_students(distinguished_student_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  evidence_role TEXT NOT NULL CHECK (evidence_role IN ('enrollment', 'program', 'achievement')),
  PRIMARY KEY (distinguished_student_id, source_id, evidence_role)
);

CREATE TABLE public_figures (
  public_figure_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  person_name TEXT NOT NULL,
  occupation TEXT,
  attendance_status TEXT NOT NULL CHECK (attendance_status IN ('graduated', 'attended', 'transferred', 'withdrew', 'unknown')),
  major TEXT,
  degree TEXT,
  graduation_year INTEGER,
  UNIQUE (university_id, person_name, attendance_status)
);

CREATE TABLE public_figure_sources (
  public_figure_id TEXT NOT NULL REFERENCES public_figures(public_figure_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  evidence_role TEXT NOT NULL CHECK (evidence_role IN ('attendance', 'major', 'degree', 'graduation_year', 'occupation')),
  PRIMARY KEY (public_figure_id, source_id, evidence_role)
);

CREATE TABLE university_history (
  university_history_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL UNIQUE REFERENCES universities(internal_id) ON DELETE CASCADE,
  founded_year INTEGER,
  history_summary_zh TEXT,
  last_verified_at TIMESTAMPTZ,
  null_reason TEXT
);

CREATE TABLE university_history_sources (
  university_history_id TEXT NOT NULL REFERENCES university_history(university_history_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (university_history_id, source_id)
);

CREATE TABLE university_anecdotes (
  anecdote_id TEXT PRIMARY KEY,
  university_id TEXT NOT NULL REFERENCES universities(internal_id) ON DELETE CASCADE,
  title_zh TEXT NOT NULL,
  content_zh TEXT NOT NULL,
  anecdote_type TEXT NOT NULL,
  confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  is_unverified_legend BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE university_anecdote_sources (
  anecdote_id TEXT NOT NULL REFERENCES university_anecdotes(anecdote_id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(source_id),
  PRIMARY KEY (anecdote_id, source_id)
);

CREATE TABLE data_quality_issues (
  issue_id TEXT PRIMARY KEY,
  university_id TEXT REFERENCES universities(internal_id) ON DELETE CASCADE,
  field_name TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  description TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  status TEXT NOT NULL CHECK (status IN ('open', 'accepted', 'resolved', 'wont_fix')),
  source_id TEXT REFERENCES sources(source_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMPTZ
);

CREATE INDEX nearby_places_university_idx ON nearby_places(university_id, rank_by_distance);
CREATE INDEX data_quality_issues_status_idx ON data_quality_issues(status, severity);
