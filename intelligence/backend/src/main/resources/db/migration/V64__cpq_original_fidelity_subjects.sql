-- Extend the existing CPQ evidence ledger; legacy candidate rows remain unchanged.
CREATE TABLE cpq_original_subjects (
  subject_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  binding_sha256 CHAR(64) NOT NULL UNIQUE,
  prompt_fingerprint CHAR(64) NOT NULL,
  approved_story_fingerprint CHAR(64) NOT NULL,
  approval_record_id UUID NOT NULL REFERENCES post_family_workflow_events(id),
  payload JSONB NOT NULL,
  bound_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (prompt_fingerprint=encode(digest(payload->>'promptText','sha256'),'hex')),
  CHECK (approved_story_fingerprint=encode(digest(payload#>>'{approvedStory,text}','sha256'),'hex')),
  CHECK (binding_sha256=payload->>'bindingSha256')
);
CREATE TRIGGER cpq_original_subjects_append_only BEFORE UPDATE OR DELETE ON cpq_original_subjects
FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();

ALTER TABLE cpq_fidelity_reviews
  ALTER COLUMN content_id DROP NOT NULL,
  ALTER COLUMN prompt_version_id DROP NOT NULL,
  ALTER COLUMN analysis_id DROP NOT NULL,
  ADD COLUMN subject_type TEXT NOT NULL DEFAULT 'OPTIMIZATION_CANDIDATE'
    CHECK (subject_type IN ('ORIGINAL_PROMPT','OPTIMIZATION_CANDIDATE')),
  ADD COLUMN original_subject_id UUID REFERENCES cpq_original_subjects(subject_id),
  ADD COLUMN review_contract_version TEXT NOT NULL DEFAULT 'candidate-fidelity-v1',
  ADD COLUMN supersedes_evidence_id UUID REFERENCES cpq_fidelity_reviews(evidence_id),
  ADD CONSTRAINT cpq_fidelity_subject_scope CHECK (
    (subject_type='ORIGINAL_PROMPT' AND original_subject_id IS NOT NULL AND comparison_id IS NULL AND analysis_id IS NULL
      AND original_prompt_fingerprint=candidate_prompt_fingerprint
      AND review_contract_version='original-fidelity-v2') OR
    (subject_type='OPTIMIZATION_CANDIDATE' AND original_subject_id IS NULL
      AND content_id IS NOT NULL AND prompt_version_id IS NOT NULL AND analysis_id IS NOT NULL)
  );
CREATE INDEX cpq_original_fidelity_idx ON cpq_fidelity_reviews(original_subject_id,created_at DESC)
  WHERE subject_type='ORIGINAL_PROMPT';
CREATE UNIQUE INDEX cpq_fidelity_superseded_once_idx ON cpq_fidelity_reviews(supersedes_evidence_id)
  WHERE supersedes_evidence_id IS NOT NULL;

ALTER TABLE cpq_calibration_examples
  ADD COLUMN fidelity_subject_type TEXT NOT NULL DEFAULT 'OPTIMIZATION_CANDIDATE'
    CHECK (fidelity_subject_type IN ('ORIGINAL_PROMPT','OPTIMIZATION_CANDIDATE')),
  ADD COLUMN source_group TEXT,
  ADD COLUMN mechanic_group TEXT,
  ADD COLUMN production_settings_fingerprint CHAR(64),
  ADD COLUMN production_settings JSONB,
  ADD COLUMN import_contract_version TEXT NOT NULL DEFAULT 'legacy-v1';

COMMENT ON TABLE cpq_original_subjects IS
  'Append-only architecture-attested original prompt/source/settings bindings. A binding is not a fidelity PASS or story approval.';
