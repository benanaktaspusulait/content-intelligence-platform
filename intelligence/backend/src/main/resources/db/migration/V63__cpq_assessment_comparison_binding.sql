ALTER TABLE cpq_assessments
  ADD COLUMN comparison_id UUID REFERENCES post_family_workflow_events(id);

ALTER TABLE cpq_fidelity_reviews
  ADD COLUMN comparison_id UUID REFERENCES post_family_workflow_events(id);

CREATE INDEX cpq_assessments_comparison_idx
  ON cpq_assessments(comparison_id, candidate_id, created_at DESC);

CREATE INDEX cpq_fidelity_comparison_idx
  ON cpq_fidelity_reviews(comparison_id, candidate_prompt_fingerprint, created_at DESC);

COMMENT ON COLUMN cpq_assessments.comparison_id IS
  'Exact immutable creative-optimization comparison selected for this candidate assessment; NULL for legacy assessments.';
COMMENT ON COLUMN cpq_fidelity_reviews.comparison_id IS
  'Exact immutable creative-optimization comparison selected for this candidate fidelity review; NULL for legacy reviews.';
