-- V10: Render Jobs and Assets tables

-- Render jobs (orchestration)
CREATE TABLE render_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    prompt_version_id BIGINT NOT NULL REFERENCES prompt_versions(id),
    
    -- Job type
    job_type VARCHAR(20) NOT NULL CHECK (job_type IN ('FIRST_FRAME', 'VIDEO')),
    
    -- OpenArt integration
    openart_job_id VARCHAR(100),
    openart_model VARCHAR(50) NOT NULL,
    openart_params JSONB,
    
    -- State tracking
    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN (
            'QUEUED', 'GENERATING', 'POLLING', 'DOWNLOADING', 
            'COMPLETE', 'FAILED', 'ABANDONED'
        )
    ),
    attempt_number INT NOT NULL DEFAULT 1,
    max_attempts INT NOT NULL DEFAULT 3,
    
    -- Cost tracking
    credits_estimated NUMERIC(10,2),
    credits_actual NUMERIC(10,2),
    
    -- Timestamps
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    
    -- Error details
    error_code VARCHAR(50),
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_jobs_content_id ON render_jobs(content_id);
CREATE INDEX idx_render_jobs_status ON render_jobs(status);
CREATE INDEX idx_render_jobs_openart_job_id ON render_jobs(openart_job_id);
CREATE INDEX idx_render_jobs_queued_at ON render_jobs(queued_at);

COMMENT ON TABLE render_jobs IS 'Render job orchestration for OpenArt generation';

-- Render assets (downloaded files)
CREATE TABLE render_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,
    content_id BIGINT NOT NULL REFERENCES contents(id),
    
    -- Asset metadata
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('FIRST_FRAME', 'VIDEO')),
    relative_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    
    -- Video-specific metadata (NULL for images)
    duration_ms INT,
    width INT NOT NULL,
    height INT NOT NULL,
    frame_rate NUMERIC(5,2),
    codec VARCHAR(50),
    
    -- Download tracking
    download_url TEXT,
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Status
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_assets_render_job_id ON render_assets(render_job_id);
CREATE INDEX idx_render_assets_content_id ON render_assets(content_id);
CREATE INDEX idx_render_assets_is_current ON render_assets(is_current);

COMMENT ON TABLE render_assets IS 'Downloaded render assets (first frames and videos)';

-- Update contents table for render tracking
ALTER TABLE contents
    ADD COLUMN current_render_asset_id UUID REFERENCES render_assets(id),
    ADD COLUMN render_status VARCHAR(30) DEFAULT 'NOT_STARTED' CHECK (
        render_status IN (
            'NOT_STARTED', 'QUEUED', 'IN_PROGRESS', 
            'COMPLETED', 'FAILED', 'ABANDONED'
        )
    );

CREATE INDEX idx_contents_render_status ON contents(render_status);
