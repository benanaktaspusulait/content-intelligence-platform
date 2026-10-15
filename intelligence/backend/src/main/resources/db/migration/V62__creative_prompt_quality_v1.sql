CREATE TABLE cpq_calibration_corpora (
  corpus_version TEXT PRIMARY KEY,
  rubric_version TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('DRAFT','REVIEWING','CALIBRATED','HELD_OUT_VALIDATED','APPROVED','INACTIVE')),
  corpus_sha256 CHAR(64),
  calibration_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  CHECK ((approved_by IS NULL) = (approved_at IS NULL))
);

CREATE TABLE cpq_calibration_examples (
  example_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  corpus_version TEXT NOT NULL REFERENCES cpq_calibration_corpora(corpus_version),
  source_story_id TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  source_fingerprint CHAR(64) NOT NULL,
  prompt_version_id BIGINT,
  prompt_fingerprint CHAR(64) NOT NULL,
  prompt_text TEXT NOT NULL,
  content_profile TEXT NOT NULL,
  generator TEXT NOT NULL,
  target_duration_seconds NUMERIC NOT NULL CHECK (target_duration_seconds > 0),
  source_fidelity_evidence_id UUID,
  observed_render_evidence JSONB,
  audience_evidence JSONB,
  case_type TEXT NOT NULL CHECK (case_type IN ('EXCELLENT_EXECUTION','STRONG_EXECUTION','ADEQUATE_IMPROVABLE','WEAK_EXECUTION','SOURCE_FAITHFUL_IMPROVEMENT','COSMETIC_REWRITE','PRODUCTION_REGRESSION','CONSTRAINED_UNIMPROVABLE','GENERAL_PROMPT')),
  split TEXT NOT NULL CHECK (split IN ('CALIBRATION','HELD_OUT')),
  provenance JSONB NOT NULL,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (encode(digest(prompt_text, 'sha256'), 'hex') = prompt_fingerprint)
);

CREATE TABLE cpq_calibration_judgments (
  judgment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  example_id UUID NOT NULL REFERENCES cpq_calibration_examples(example_id),
  reviewer_principal TEXT NOT NULL,
  reviewer_role TEXT NOT NULL CHECK (reviewer_role = 'CREATIVE_QUALITY_REVIEWER'),
  rubric_version TEXT NOT NULL,
  review_method_version TEXT NOT NULL,
  dimension_judgments JSONB NOT NULL,
  source_fidelity_decision TEXT NOT NULL CHECK (source_fidelity_decision IN ('PASS','FAIL','UNKNOWN')),
  overall_quality_anchor TEXT NOT NULL CHECK (overall_quality_anchor IN ('A+','A','B','C','F','UNKNOWN')),
  evidence_citations JSONB NOT NULL,
  confidence JSONB NOT NULL,
  reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (example_id, reviewer_principal, rubric_version)
);

CREATE TABLE cpq_fidelity_reviews (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id BIGINT NOT NULL,
  prompt_version_id BIGINT NOT NULL REFERENCES prompt_versions(id),
  approved_story_id TEXT NOT NULL,
  approved_revision TEXT NOT NULL,
  approved_story_fingerprint CHAR(64) NOT NULL,
  original_prompt_fingerprint CHAR(64) NOT NULL,
  candidate_prompt_fingerprint CHAR(64) NOT NULL,
  intervention_fingerprint CHAR(64) NOT NULL,
  changed_beat_ids JSONB NOT NULL,
  source_event_mapping JSONB NOT NULL,
  analysis_id UUID NOT NULL,
  ruleset_version TEXT NOT NULL,
  cpq_rubric_version TEXT NOT NULL,
  production_settings_fingerprint CHAR(64) NOT NULL,
  reviewer_principal TEXT NOT NULL,
  reviewer_authority TEXT NOT NULL CHECK (reviewer_authority = 'EVIDENCE_REVIEWER'),
  review_method_version TEXT NOT NULL,
  citations JSONB NOT NULL,
  rationale TEXT NOT NULL CHECK (length(trim(rationale)) >= 20),
  decision TEXT NOT NULL CHECK (decision IN ('PASS','FAIL','UNKNOWN')),
  valid_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE cpq_calibration_examples
  ADD CONSTRAINT cpq_calibration_fidelity_fk FOREIGN KEY (source_fidelity_evidence_id)
  REFERENCES cpq_fidelity_reviews(evidence_id);

CREATE TABLE cpq_assessments (
  assessment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID NOT NULL,
  content_id BIGINT NOT NULL,
  prompt_version_id BIGINT NOT NULL,
  candidate_id TEXT NOT NULL,
  original_prompt_fingerprint CHAR(64) NOT NULL,
  candidate_prompt_fingerprint CHAR(64) NOT NULL,
  ruleset_version TEXT NOT NULL,
  rubric_version TEXT NOT NULL,
  calibration_corpus_version TEXT,
  fidelity_evidence_id UUID REFERENCES cpq_fidelity_reviews(evidence_id),
  result JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (analysis_id, candidate_id, candidate_prompt_fingerprint, rubric_version)
);

CREATE TABLE cpq_policy_state (
  singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
  rubric_version TEXT NOT NULL,
  corpus_version TEXT,
  activated BOOLEAN NOT NULL DEFAULT FALSE,
  activation_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  changed_by TEXT,
  changed_at TIMESTAMPTZ,
  CHECK (activated = FALSE OR (corpus_version IS NOT NULL AND changed_by IS NOT NULL AND changed_at IS NOT NULL))
);
INSERT INTO cpq_policy_state(singleton, rubric_version, activated) VALUES (TRUE, 'creative-prompt-quality-v1', FALSE);

CREATE OR REPLACE FUNCTION prevent_cpq_evidence_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'CPQ calibration and review evidence is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cpq_calibration_examples_append_only BEFORE UPDATE OR DELETE ON cpq_calibration_examples
FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE TRIGGER cpq_calibration_judgments_append_only BEFORE UPDATE OR DELETE ON cpq_calibration_judgments
FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE TRIGGER cpq_fidelity_reviews_append_only BEFORE UPDATE OR DELETE ON cpq_fidelity_reviews
FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE TRIGGER cpq_assessments_append_only BEFORE UPDATE OR DELETE ON cpq_assessments
FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();

COMMENT ON TABLE cpq_fidelity_reviews IS 'Authenticated, candidate-bound human source-fidelity evidence; UNKNOWN unless independently reviewed.';
COMMENT ON TABLE cpq_calibration_examples IS 'Source-authorized prompt examples with separately labelled calibration and held-out splits; no grades are inferred on import.';
COMMENT ON TABLE cpq_calibration_judgments IS 'Append-only blinded human dimension judgments for CPQ calibration.';
COMMENT ON TABLE cpq_policy_state IS 'CPQ grading remains inactive until explicit activation evidence is present.';
