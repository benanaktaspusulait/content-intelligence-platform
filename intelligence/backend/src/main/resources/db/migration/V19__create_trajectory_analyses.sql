-- V19: Create trajectory analysis table

CREATE TABLE trajectory_analyses (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL UNIQUE REFERENCES publication_jobs(id) ON DELETE CASCADE,
    
    -- Velocity metrics
    velocity_first_hour DECIMAL(10,2),
    velocity_first_6h DECIMAL(10,2),
    velocity_first_24h DECIMAL(10,2),
    velocity_day_1_to_7 DECIMAL(10,2),
    velocity_day_7_to_30 DECIMAL(10,2),
    
    -- Acceleration metrics
    acceleration_1h_to_6h DECIMAL(10,2),
    acceleration_6h_to_24h DECIMAL(10,2),
    acceleration_day_1_to_7 DECIMAL(10,2),
    
    -- Peak detection
    peak_views BIGINT,
    peak_timestamp TIMESTAMP,
    peak_day INTEGER,
    time_to_peak_hours INTEGER,
    
    -- Plateau detection
    plateau_detected BOOLEAN DEFAULT FALSE,
    plateau_timestamp TIMESTAMP,
    plateau_day INTEGER,
    plateau_views BIGINT,
    
    -- Decay detection
    decay_detected BOOLEAN DEFAULT FALSE,
    decay_rate DECIMAL(5,2),
    
    -- Wave detection
    wave_count INTEGER DEFAULT 0,
    primary_wave_day INTEGER,
    primary_wave_views BIGINT,
    secondary_wave_day INTEGER,
    secondary_wave_views BIGINT,
    tertiary_wave_day INTEGER,
    tertiary_wave_views BIGINT,
    
    -- Tail analysis
    tail_strength DECIMAL(5,4),
    tail_velocity DECIMAL(10,2),
    tail_sustainability_score DECIMAL(5,2),
    
    -- Trajectory shape
    trajectory_shape VARCHAR(30),
    growth_pattern VARCHAR(50),
    
    -- Metadata
    data_points_count INTEGER,
    analysis_confidence DECIMAL(5,2),
    analyzed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trajectory_analyses_job ON trajectory_analyses(publication_job_id);
CREATE INDEX idx_trajectory_analyses_shape ON trajectory_analyses(trajectory_shape);
CREATE INDEX idx_trajectory_analyses_velocity ON trajectory_analyses(velocity_first_24h DESC);
CREATE INDEX idx_trajectory_analyses_waves ON trajectory_analyses(wave_count DESC);
CREATE INDEX idx_trajectory_analyses_tail ON trajectory_analyses(tail_strength DESC);

COMMENT ON TABLE trajectory_analyses IS 'Detailed trajectory analysis with velocity, acceleration, waves, plateau, decay detection';
COMMENT ON COLUMN trajectory_analyses.velocity_first_hour IS 'Views per hour in first hour';
COMMENT ON COLUMN trajectory_analyses.velocity_first_24h IS 'Average views per hour in first 24 hours';
COMMENT ON COLUMN trajectory_analyses.acceleration_6h_to_24h IS 'Change in velocity from 6h to 24h';
COMMENT ON COLUMN trajectory_analyses.tail_strength IS 'Percentage of views after day 7';
COMMENT ON COLUMN trajectory_analyses.tail_sustainability_score IS 'Score 0-100 for sustained tail growth';
COMMENT ON COLUMN trajectory_analyses.trajectory_shape IS 'HOCKEY_STICK, EXPONENTIAL, LINEAR, S_CURVE, SPIKE_AND_PLATEAU, SPIKE_AND_DECAY, MULTI_WAVE, FLAT, DECLINING';
