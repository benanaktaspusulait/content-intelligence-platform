CREATE TABLE quality_validation_visual_evidence (
  id BIGSERIAL PRIMARY KEY,
  validation_record_id BIGINT NOT NULL REFERENCES quality_validations(id) ON DELETE RESTRICT,
  content_id BIGINT NOT NULL,
  prompt_version_id BIGINT NOT NULL,
  prompt_sha256 TEXT NOT NULL,
  visual_gate VARCHAR(32) NOT NULL CHECK (visual_gate IN ('FIRST_FRAME', 'SILHOUETTE')),
  status VARCHAR(16) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'PENDING', 'UNKNOWN')),
  evidence_set_id UUID,
  render_job_id UUID,
  render_asset_id UUID,
  asset_type VARCHAR(32),
  asset_relative_path TEXT,
  asset_sha256 TEXT,
  provenance_json JSONB,
  reason TEXT NOT NULL,
  verification_id VARCHAR(200),
  verified_at TIMESTAMPTZ,
  submission_key VARCHAR(200) NOT NULL UNIQUE,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT quality_validation_visual_evidence_sha_check
    CHECK (prompt_sha256 ~ '^[0-9a-f]{64}$' AND (asset_sha256 IS NULL OR asset_sha256 ~ '^[0-9a-f]{64}$'))
);

CREATE INDEX idx_quality_visual_evidence_latest
  ON quality_validation_visual_evidence(validation_record_id, visual_gate, submitted_at DESC, id DESC);

CREATE OR REPLACE FUNCTION reject_quality_visual_evidence_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'quality_validation_visual_evidence is append-only';
END;
$$;

CREATE TRIGGER quality_validation_visual_evidence_append_only
BEFORE UPDATE OR DELETE ON quality_validation_visual_evidence
FOR EACH ROW EXECUTE FUNCTION reject_quality_visual_evidence_mutation();
