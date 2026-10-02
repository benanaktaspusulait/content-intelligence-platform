-- Publication jobs table for tracking social media uploads
CREATE TABLE publication_jobs (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    video_path TEXT NOT NULL,
    title VARCHAR(500),
    caption TEXT,
    hashtags TEXT,
    is_private BOOLEAN,
    platform_post_id VARCHAR(100),
    platform_video_id VARCHAR(100),
    post_url TEXT,
    progress_percent INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    queued_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_publication_jobs_platform ON publication_jobs(platform);
CREATE INDEX idx_publication_jobs_status ON publication_jobs(status);
CREATE INDEX idx_publication_jobs_queued_at ON publication_jobs(queued_at);
CREATE INDEX idx_publication_jobs_platform_status ON publication_jobs(platform, status);

COMMENT ON TABLE publication_jobs IS 'Social media publication jobs with state tracking';
COMMENT ON COLUMN publication_jobs.platform IS 'Platform: TIKTOK, YOUTUBE, FACEBOOK, INSTAGRAM';
COMMENT ON COLUMN publication_jobs.status IS 'Status: QUEUED, UPLOADING, PROCESSING, PUBLISHED, FAILED, CANCELLED';
COMMENT ON COLUMN publication_jobs.progress_percent IS 'Upload progress 0-100';
COMMENT ON COLUMN publication_jobs.retry_count IS 'Number of retry attempts';
