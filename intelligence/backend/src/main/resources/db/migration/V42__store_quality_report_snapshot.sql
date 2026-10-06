-- Persist the full quality report so a previously analysed prompt can be shown again
-- without re-running the ML service. Additive and nullable: existing rows keep only their
-- summary columns and simply have no snapshot.

ALTER TABLE quality_validations
  ADD COLUMN report_json TEXT,
  ADD COLUMN prompt_fingerprint VARCHAR(64);

CREATE INDEX idx_quality_validations_fingerprint_created
  ON quality_validations(prompt_fingerprint, id DESC)
  WHERE prompt_fingerprint IS NOT NULL AND report_json IS NOT NULL;

COMMENT ON COLUMN quality_validations.report_json IS
  'JSON snapshot of the full QualityReportDto returned to the UI for this validation.';
COMMENT ON COLUMN quality_validations.prompt_fingerprint IS
  'SHA-256 (lowercase hex) of the validated prompt text, used to find the latest analysis of an unlinked prompt. Not evidence: see prompt_sha256 for linked evidence.';
