CREATE TABLE visual_reference_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID NOT NULL UNIQUE REFERENCES render_jobs(id),
    content_id BIGINT NOT NULL,
    prompt_version_id BIGINT NOT NULL,
    prompt_sha256 VARCHAR(64) NOT NULL,
    provider VARCHAR(80) NOT NULL,
    model VARCHAR(120) NOT NULL,
    first_frame_status VARCHAR(40) NOT NULL,
    strategy VARCHAR(60) NOT NULL,
    validation_status VARCHAR(40) NOT NULL,
    recommendation JSONB NOT NULL DEFAULT '{}'::jsonb,
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    cost_estimate JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visual_reference_plans_content ON visual_reference_plans(content_id, prompt_version_id);

CREATE TABLE visual_reference_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES visual_reference_plans(id),
    role VARCHAR(40) NOT NULL CHECK (role IN ('CHARACTER_REFERENCE', 'SCENE_REFERENCE', 'FIRST_FRAME', 'CRITICAL_SCENE', 'END_FRAME', 'TRANSITION_REFERENCE')),
    source_kind VARCHAR(20) NOT NULL CHECK (source_kind IN ('EXISTING', 'IMPORTED', 'GENERATED')),
    render_asset_id UUID REFERENCES render_assets(id),
    canonical_key VARCHAR(240),
    relative_path TEXT,
    provider_asset_id VARCHAR(200),
    sha256 VARCHAR(64),
    prompt_sha256 VARCHAR(64),
    intended_beat_id VARCHAR(160),
    intended_state TEXT,
    validation_status VARCHAR(40) NOT NULL DEFAULT 'UNKNOWN',
    validation_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_visual_reference_assets_plan ON visual_reference_assets(plan_id, role);
