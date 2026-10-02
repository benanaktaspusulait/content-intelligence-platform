-- V22: Create winner entries table

CREATE TABLE winner_entries (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    winner_tier VARCHAR(30) NOT NULL,
    performance_category VARCHAR(30) NOT NULL,
    
    -- Key metrics snapshot
    total_views BIGINT NOT NULL,
    total_engagement BIGINT NOT NULL,
    engagement_rate DECIMAL(5,2),
    completion_rate DECIMAL(5,2),
    velocity_first_24h DECIMAL(10,2),
    tail_strength DECIMAL(5,4),
    
    -- Trajectory characteristics
    trajectory_shape VARCHAR(30),
    peak_day INTEGER,
    wave_count INTEGER,
    
    -- Benchmark scores
    benchmark_score DECIMAL(5,2),
    percentile_rank DECIMAL(5,2),
    
    -- Metadata
    notes TEXT,
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_winner_entries_job ON winner_entries(publication_job_id);
CREATE INDEX idx_winner_entries_tier ON winner_entries(winner_tier);
CREATE INDEX idx_winner_entries_category ON winner_entries(performance_category);
CREATE INDEX idx_winner_entries_score ON winner_entries(benchmark_score DESC);
CREATE INDEX idx_winner_entries_trajectory ON winner_entries(trajectory_shape);
CREATE INDEX idx_winner_entries_percentile ON winner_entries(percentile_rank DESC);

COMMENT ON TABLE winner_entries IS 'Catalog of top-performing videos for benchmarking and comparison';
COMMENT ON COLUMN winner_entries.winner_tier IS 'PLATINUM (top 1%), GOLD (top 5%), SILVER (top 10%), BRONZE (top 25%)';
COMMENT ON COLUMN winner_entries.benchmark_score IS 'Composite score 0-100: views 30%, engagement 25%, velocity 20%, completion 15%, tail 10%';
COMMENT ON COLUMN winner_entries.percentile_rank IS 'Percentile rank among all videos 0-100';
