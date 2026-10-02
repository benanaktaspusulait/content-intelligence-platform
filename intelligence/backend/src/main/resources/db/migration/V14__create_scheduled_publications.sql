-- Scheduled publications table
CREATE TABLE scheduled_publications (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    video_path TEXT NOT NULL,
    title VARCHAR(500),
    caption TEXT,
    hashtags TEXT,
    is_private BOOLEAN,
    scheduled_at TIMESTAMP NOT NULL,
    timezone VARCHAR(50),
    is_executed BOOLEAN NOT NULL DEFAULT FALSE,
    executed_at TIMESTAMP,
    publication_job_id UUID,
    created_by VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduled_publications_platform ON scheduled_publications(platform);
CREATE INDEX idx_scheduled_publications_scheduled_at ON scheduled_publications(scheduled_at);
CREATE INDEX idx_scheduled_publications_is_executed ON scheduled_publications(is_executed);
CREATE INDEX idx_scheduled_publications_due ON scheduled_publications(is_executed, scheduled_at);

COMMENT ON TABLE scheduled_publications IS 'Scheduled social media publications';
COMMENT ON COLUMN scheduled_publications.scheduled_at IS 'When to publish (UTC)';
COMMENT ON COLUMN scheduled_publications.timezone IS 'Original timezone for scheduling';
COMMENT ON COLUMN scheduled_publications.is_executed IS 'Whether publication has been queued';
COMMENT ON COLUMN scheduled_publications.publication_job_id IS 'Reference to created publication job';
