-- V26: Create Reach Further events tracking

CREATE TABLE reach_further_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_job_id UUID NOT NULL,
    platform VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Performance snapshots
    views_before BIGINT,
    views_1h_after BIGINT,
    views_3h_after BIGINT,
    views_6h_after BIGINT,
    views_24h_after BIGINT,
    
    -- Audience distribution
    country_distribution_snapshot TEXT, -- JSON: {"US": 45.2, "TR": 23.1, ...}
    follower_percentage DECIMAL(5,2),
    non_follower_percentage DECIMAL(5,2),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (publication_job_id) REFERENCES publication_jobs(id) ON DELETE CASCADE
);

COMMENT ON TABLE reach_further_events IS 'Track Reach Further state detection and performance impact';
COMMENT ON COLUMN reach_further_events.country_distribution_snapshot IS 'Geographic distribution at detection time (JSON)';

-- Indexes
CREATE INDEX idx_reach_further_publication ON reach_further_events(publication_job_id);
CREATE INDEX idx_reach_further_platform ON reach_further_events(platform);
CREATE INDEX idx_reach_further_detected ON reach_further_events(detected_at DESC);
CREATE INDEX idx_reach_further_platform_date ON reach_further_events(platform, detected_at DESC);
