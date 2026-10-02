-- V11: Render QA Results and OpenArt Credit Log tables

-- Render QA results
CREATE TABLE render_qa_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id) ON DELETE CASCADE,
    prompt_version_id BIGINT NOT NULL REFERENCES prompt_versions(id),
    
    -- Overall decision
    decision VARCHAR(30) NOT NULL CHECK (
        decision IN ('ACCEPT', 'RERENDER', 'ABANDON')
    ),
    decision_reason TEXT NOT NULL,
    confidence NUMERIC(3,2),
    
    -- Compliance checks
    compliance_score INT NOT NULL,
    compliance_issues JSONB,
    
    -- Technical checks
    has_dead_air BOOLEAN NOT NULL,
    dead_air_segments JSONB,
    
    character_identity_verified BOOLEAN NOT NULL,
    character_identity_issues TEXT,
    
    physics_consistent BOOLEAN NOT NULL,
    physics_violations TEXT,
    
    has_object_duplication BOOLEAN NOT NULL,
    duplication_details TEXT,
    
    -- Final execution check
    final_execution_score INT,
    final_execution_issues TEXT,
    
    -- Human review
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    human_reviewed_at TIMESTAMPTZ,
    human_reviewer VARCHAR(50),
    human_decision VARCHAR(30),
    human_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_qa_results_render_asset_id ON render_qa_results(render_asset_id);
CREATE INDEX idx_render_qa_results_decision ON render_qa_results(decision);
CREATE INDEX idx_render_qa_results_requires_human_review ON render_qa_results(requires_human_review);

COMMENT ON TABLE render_qa_results IS 'Quality assurance results for rendered assets';

-- OpenArt credit tracking
CREATE TABLE openart_credit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID REFERENCES render_jobs(id),
    
    -- Operation details
    operation VARCHAR(50) NOT NULL,
    operation_metadata JSONB,
    
    -- Credit balance
    credits_before NUMERIC(10,2),
    credits_spent NUMERIC(10,2) NOT NULL DEFAULT 0,
    credits_after NUMERIC(10,2),
    
    -- Metadata
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_openart_credit_log_render_job_id ON openart_credit_log(render_job_id);
CREATE INDEX idx_openart_credit_log_logged_at ON openart_credit_log(logged_at);
CREATE INDEX idx_openart_credit_log_operation ON openart_credit_log(operation);

COMMENT ON TABLE openart_credit_log IS 'OpenArt credit usage tracking';
