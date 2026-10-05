CREATE TABLE post_render_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL UNIQUE REFERENCES post_render_evaluations(id),
    grade VARCHAR(20) NOT NULL,
    label VARCHAR(120) NOT NULL,
    verdict TEXT NOT NULL,
    evidence_coverage_percent INT NOT NULL,
    assessment_version VARCHAR(80) NOT NULL,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_post_render_assessments_evaluation
    ON post_render_assessments(evaluation_id);
