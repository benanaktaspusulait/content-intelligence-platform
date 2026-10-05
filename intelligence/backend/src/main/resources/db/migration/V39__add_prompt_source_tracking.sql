ALTER TABLE contents
  ADD COLUMN source_path TEXT;

CREATE UNIQUE INDEX uq_contents_source_path
  ON contents(source_path)
  WHERE source_path IS NOT NULL;

ALTER TABLE prompt_versions
  ADD COLUMN source_path TEXT,
  ADD COLUMN source_sha256 VARCHAR(64);

CREATE UNIQUE INDEX uq_prompt_versions_source_hash
  ON prompt_versions(source_path, source_sha256)
  WHERE source_path IS NOT NULL AND source_sha256 IS NOT NULL;

COMMENT ON COLUMN contents.source_path IS
  'Canonical mounted-library prompt source used by the DB-backed workspace.';
COMMENT ON COLUMN prompt_versions.source_path IS
  'Mounted-library file from which this immutable prompt version was imported.';
COMMENT ON COLUMN prompt_versions.source_sha256 IS
  'SHA-256 of the imported source file for idempotent synchronization.';
