-- V25: Add creative engine tracking and intervention fields based on strategic decisions

-- Add creative engine tracking to contents
ALTER TABLE contents ADD COLUMN creative_engine VARCHAR(50);
ALTER TABLE contents ADD COLUMN engine_variant VARCHAR(100);
ALTER TABLE contents ADD COLUMN first_frame_anomaly_type VARCHAR(50);
ALTER TABLE contents ADD COLUMN hook_visible_first_frame BOOLEAN DEFAULT false;
ALTER TABLE contents ADD COLUMN content_lane VARCHAR(10) DEFAULT 'STOCK';

COMMENT ON COLUMN contents.creative_engine IS 'Creative engine (Engine1-10): IMPOSSIBLE_PHYSICAL, RUNAWAY_OBJECT, LIVING_OBJECTS, etc.';
COMMENT ON COLUMN contents.content_lane IS 'Publishing lane: STOCK (educational) or WINNER (hit-candidate)';
COMMENT ON COLUMN contents.first_frame_anomaly_type IS 'Hook type: SCALE, POSITION, RESISTANCE, MOVEMENT, TRANSFORMATION';

-- Add manual intervention tracking to publication_jobs
ALTER TABLE publication_jobs ADD COLUMN manual_intervention BOOLEAN DEFAULT false;
ALTER TABLE publication_jobs ADD COLUMN intervention_type VARCHAR(50);
ALTER TABLE publication_jobs ADD COLUMN intervention_timestamp TIMESTAMP WITH TIME ZONE;
ALTER TABLE publication_jobs ADD COLUMN intervention_notes TEXT;
ALTER TABLE publication_jobs ADD COLUMN is_prime_slot BOOLEAN DEFAULT false;

COMMENT ON COLUMN publication_jobs.manual_intervention IS 'Flag videos with manual engagement/nudges';
COMMENT ON COLUMN publication_jobs.is_prime_slot IS 'Published in prime testing slot';

-- Add success tier to performance_classifications
ALTER TABLE performance_classifications ADD COLUMN success_tier VARCHAR(20);

COMMENT ON COLUMN performance_classifications.success_tier IS 'Success tier: FAILURE, NORMAL, GOOD, WINNER, BREAKOUT';

-- Indexes for new fields
CREATE INDEX idx_contents_creative_engine ON contents(creative_engine);
CREATE INDEX idx_contents_content_lane ON contents(content_lane);
CREATE INDEX idx_contents_first_frame_anomaly ON contents(first_frame_anomaly_type);
CREATE INDEX idx_publication_jobs_manual_intervention ON publication_jobs(manual_intervention);
CREATE INDEX idx_publication_jobs_prime_slot ON publication_jobs(is_prime_slot);
CREATE INDEX idx_performance_success_tier ON performance_classifications(success_tier);
