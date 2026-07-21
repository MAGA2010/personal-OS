-- Gate 1 hardening: a program ranking's category is defined only by its snapshot.
-- 002 created this redundant column before the Gate 1 audit; retain history and
-- remove the duplicate truth source with an incremental migration.

ALTER TABLE program_rankings DROP COLUMN ranking_category;
