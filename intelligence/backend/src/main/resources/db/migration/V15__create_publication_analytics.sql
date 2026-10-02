-- Publication analytics table
CREATE TABLE publication_analytics (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL,
    platform VARCHAR(20) NOT NULL,
    platform_post_id VARCHAR(100),
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    saves BIGINT,
    engagement_rate DOUBLE PRECISION,
    watch_time_seconds BIGINT,
    average_view_duration_seconds DOUBLE PRECISION,
    impressions BIGINT,
    reach BIGINT,
    clicks BIGINT,
    fetched_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publication_job_id)
);

CREATE INDEX idx_publication_analytics_job_id ON publication_analytics(publication_job_id);
CREATE INDEX idx_publication_analytics_platform ON publication_analytics(platform);
CREATE INDEX idx_publication_analytics_views ON publication_analytics(views DESC);
CREATE INDEX idx_publication_analytics_engagement ON publication_analytics(engagement_rate DESC);
CREATE INDEX idx_publication_analytics_fetched_at ON publication_analytics(fetched_at);

COMMENT ON TABLE publication_analytics IS 'Performance metrics for published content';
COMMENT ON COLUMN publication_analytics.engagement_rate IS 'Calculated as (likes + comments + shares + saves) / views * 100';
COMMENT ON COLUMN publication_analytics.watch_time_seconds IS 'Total watch time (YouTube)';
COMMENT ON COLUMN publication_analytics.impressions IS 'Number of times content was shown';
COMMENT ON COLUMN publication_analytics.reach IS 'Unique users who saw content';
