ALTER TABLE qa_human_reviews
  ALTER COLUMN render_qa_result_id DROP NOT NULL;

ALTER TABLE qa_human_reviews
  ADD COLUMN post_render_evaluation_id UUID REFERENCES post_render_evaluations(id);

ALTER TABLE qa_human_reviews
  ADD CONSTRAINT qa_human_reviews_one_subject_check
  CHECK ((render_qa_result_id IS NOT NULL) <> (post_render_evaluation_id IS NOT NULL));

CREATE INDEX idx_qa_human_reviews_evaluation_created
  ON qa_human_reviews(post_render_evaluation_id, created_at DESC);
