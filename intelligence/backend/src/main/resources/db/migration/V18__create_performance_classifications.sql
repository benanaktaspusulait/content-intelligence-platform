-- V18: Create performance classification table

CREATE TABLE performance_classifications (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    
    -- Key metrics
    final_views BIGINT,
    final_engagement_rate DECIMAL(5,2),
    peak_views BIGINT,
    peak_day INTEGER,
    
    -- Growth characteristics
    velocity_score DECIMAL(5,2),
    acceleration_score DECIMAL(5,2),
    plateau_detected BOOLEAN,
    plateau_day INTEGER,
    tail_strength DECIMAL(5,2),
    
    -- Wave detection
    primary_wave_day INTEGER,
    secondary_wave_day INTEGER,
    wave_count INTEGER,
    
    -- Metadata
    classification_reason TEXT,
    classified_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_performance_classifications_job ON performance_classifications(publication_job_id);
CREATE INDEX idx_performance_classifications_category ON performance_classifications(category);
CREATE INDEX idx_performance_classifications_final_views ON performance_classifications(final_views DESC);
CREATE INDEX idx_performance_classifications_winners ON performance_classifications(category) 
    WHERE category IN ('BREAKOUT', 'DELAYED_BREAKOUT', 'MULTI_WAVE', 'PERSISTENT_WINNER', 'EVERGREEN_BREAKOUT');

COMMENT ON TABLE performance_classifications IS 'Video performance classifications based on trajectory analysis';
COMMENT ON COLUMN performance_classifications.category IS 'Performance category: EARLY_REJECTION, WEAK, MEDIUM, STRONG_START, BREAKOUT, DELAYED_BREAKOUT, MULTI_WAVE, PERSISTENT_WINNER, LONG_TAIL, EVERGREEN_BREAKOUT';
COMMENT ON COLUMN performance_classifications.velocity_score IS 'Views per hour in first 24h';
COMMENT ON COLUMN performance_classifications.tail_strength IS 'Percentage of views after day 7';
COMMENT ON COLUMN performance_classifications.wave_count IS 'Number of distinct growth waves detected';
