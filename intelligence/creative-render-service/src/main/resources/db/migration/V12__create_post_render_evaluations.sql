CREATE TABLE post_render_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id),
    render_attempt_id UUID,
    evidence_version VARCHAR(80) NOT NULL,
    post_render_ruleset_version VARCHAR(80) NOT NULL,
    analyzer_versions JSONB NOT NULL,
    evidence_snapshot JSONB NOT NULL,
    overall_decision VARCHAR(30) NOT NULL CHECK (overall_decision IN ('PASS', 'HUMAN_REVIEW', 'FAIL', 'SYSTEM_ERROR')),
    human_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    human_reviewed_at TIMESTAMPTZ,
    human_reviewer VARCHAR(200),
    human_decision VARCHAR(30),
    human_notes TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_post_render_evaluations_asset_created
    ON post_render_evaluations(render_asset_id, created_at DESC);

CREATE TABLE post_render_rule_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES post_render_evaluations(id) ON DELETE CASCADE,
    rule_id VARCHAR(120) NOT NULL,
    rule_version VARCHAR(30) NOT NULL,
    ruleset_version VARCHAR(80) NOT NULL,
    stage VARCHAR(30) NOT NULL,
    family VARCHAR(80) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    outcome VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    actual_value JSONB,
    expected_condition JSONB NOT NULL,
    evidence_references JSONB NOT NULL,
    evaluator VARCHAR(120) NOT NULL,
    review_required BOOLEAN NOT NULL DEFAULT FALSE,
    evaluated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_post_render_rule_results_evaluation
    ON post_render_rule_results(evaluation_id);
