-- V27: Create follower metrics and conversion tracking

CREATE TABLE follower_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_job_id UUID NOT NULL,
    
    -- Follower growth
    followers_before INTEGER,
    followers_after INTEGER,
    followers_gained INTEGER,
    profile_visits INTEGER,
    follower_conversion_rate DECIMAL(5,2), -- (followers_gained / profile_visits) * 100
    
    -- Audience composition
    us_audience_percentage DECIMAL(5,2),
    non_follower_percentage DECIMAL(5,2),
    
    -- Geographic breakdown
    top_countries TEXT, -- JSON: [{"country": "US", "percentage": 45.2}, ...]
    
    -- Discovery metrics
    discovery_score DECIMAL(5,2), -- Custom score combining non-follower % and US audience
    
    -- Timestamp
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (publication_job_id) REFERENCES publication_jobs(id) ON DELETE CASCADE
);

COMMENT ON TABLE follower_metrics IS 'Track follower conversion and audience discovery metrics';
COMMENT ON COLUMN follower_metrics.discovery_score IS 'Non-follower weight 0.65 + US audience weight 0.35';

-- Indexes
CREATE INDEX idx_follower_metrics_publication ON follower_metrics(publication_job_id);
CREATE INDEX idx_follower_metrics_measured ON follower_metrics(measured_at DESC);
CREATE INDEX idx_follower_metrics_conversion ON follower_metrics(follower_conversion_rate DESC);
CREATE INDEX idx_follower_metrics_discovery ON follower_metrics(discovery_score DESC);
