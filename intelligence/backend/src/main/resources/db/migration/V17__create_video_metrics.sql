-- V17: Create video metrics collection tables

CREATE TABLE video_metrics (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    platform_video_id VARCHAR(100) NOT NULL,
    
    -- Basic engagement metrics
    views BIGINT NOT NULL DEFAULT 0,
    likes BIGINT NOT NULL DEFAULT 0,
    comments BIGINT NOT NULL DEFAULT 0,
    shares BIGINT NOT NULL DEFAULT 0,
    saves BIGINT NOT NULL DEFAULT 0,
    
    -- Retention metrics
    completion_rate DECIMAL(5,2),
    avg_watch_time_seconds DECIMAL(6,2),
    total_watch_time_seconds BIGINT,
    impressions BIGINT,
    reach BIGINT,
    clicks BIGINT,
    
    -- Platform-specific data
    platform_specific_data JSONB,
    
    -- Collection timing
    collected_at TIMESTAMP NOT NULL,
    time_since_publish_minutes INTEGER NOT NULL,
    
    -- Metadata
    collection_source VARCHAR(50),
    is_final BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_video_metrics_publication_job ON video_metrics(publication_job_id);
CREATE INDEX idx_video_metrics_platform_video ON video_metrics(platform_video_id);
CREATE INDEX idx_video_metrics_collected_at ON video_metrics(collected_at);
CREATE INDEX idx_video_metrics_is_final ON video_metrics(is_final) WHERE is_final = TRUE;

CREATE TABLE metrics_collection_jobs (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    collection_point VARCHAR(20) NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    collected_metrics_id UUID REFERENCES video_metrics(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_metrics_collection_jobs_publication ON metrics_collection_jobs(publication_job_id);
CREATE INDEX idx_metrics_collection_jobs_scheduled ON metrics_collection_jobs(scheduled_at);
CREATE INDEX idx_metrics_collection_jobs_status ON metrics_collection_jobs(status);
CREATE INDEX idx_metrics_collection_jobs_due ON metrics_collection_jobs(status, scheduled_at) 
    WHERE status = 'PENDING';

COMMENT ON TABLE video_metrics IS 'Video performance metrics collected at scheduled intervals';
COMMENT ON TABLE metrics_collection_jobs IS 'Scheduled metrics collection jobs (T+30m, T+1h, T+6h, T+24h, T+7d, T+30d)';
COMMENT ON COLUMN video_metrics.time_since_publish_minutes IS 'Minutes elapsed since video publication';
COMMENT ON COLUMN video_metrics.is_final IS 'True for T+30d final collection point';
COMMENT ON COLUMN metrics_collection_jobs.collection_point IS 'Collection timing: T+30M, T+1H, T+6H, T+24H, T+7D, T+30D';
