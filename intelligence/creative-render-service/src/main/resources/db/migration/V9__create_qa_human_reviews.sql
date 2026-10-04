CREATE TABLE qa_human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_qa_result_id UUID NOT NULL REFERENCES render_qa_results(id),
    decision VARCHAR(30) NOT NULL,
    reviewer VARCHAR(200) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_qa_human_reviews_result_created
    ON qa_human_reviews(render_qa_result_id, created_at DESC);
