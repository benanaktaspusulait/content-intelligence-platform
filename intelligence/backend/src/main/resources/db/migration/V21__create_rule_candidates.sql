-- V21: Create rule candidates table

CREATE TABLE rule_candidates (
    id UUID PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    rule_description TEXT NOT NULL,
    condition TEXT NOT NULL,
    outcome TEXT NOT NULL,
    rule_type VARCHAR(30) NOT NULL,
    rule_category VARCHAR(30) NOT NULL,
    
    -- Statistical evidence
    support_count INTEGER NOT NULL,
    total_cases INTEGER NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    lift DECIMAL(5,2),
    
    -- Actionability
    is_actionable BOOLEAN NOT NULL DEFAULT TRUE,
    action_recommendation TEXT,
    
    -- Validation
    validation_status VARCHAR(30) DEFAULT 'CANDIDATE',
    validated_at TIMESTAMP,
    validation_notes TEXT,
    
    -- Metadata
    mining_run_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rule_candidates_rule_type ON rule_candidates(rule_type);
CREATE INDEX idx_rule_candidates_rule_category ON rule_candidates(rule_category);
CREATE INDEX idx_rule_candidates_validation_status ON rule_candidates(validation_status);
CREATE INDEX idx_rule_candidates_confidence ON rule_candidates(confidence DESC);
CREATE INDEX idx_rule_candidates_mining_run ON rule_candidates(mining_run_id);
CREATE INDEX idx_rule_candidates_actionable ON rule_candidates(is_actionable, validation_status);

COMMENT ON TABLE rule_candidates IS 'Mined rule candidates from performance pattern analysis';
COMMENT ON COLUMN rule_candidates.condition IS 'IF condition (e.g., trajectory_shape = HOCKEY_STICK)';
COMMENT ON COLUMN rule_candidates.outcome IS 'THEN outcome (e.g., category = BREAKOUT)';
COMMENT ON COLUMN rule_candidates.confidence IS 'P(outcome | condition) percentage 0-100';
COMMENT ON COLUMN rule_candidates.lift IS 'Association rule lift score';
COMMENT ON COLUMN rule_candidates.rule_type IS 'TRAJECTORY_PATTERN, PERFORMANCE_THRESHOLD, CORRELATION_INSIGHT, TEMPORAL_PATTERN, COMPOSITE';
COMMENT ON COLUMN rule_candidates.rule_category IS 'EARLY_DETECTION, BREAKOUT_SIGNAL, OPTIMIZATION_HINT, WARNING_SIGNAL, BENCHMARK_RULE';
COMMENT ON COLUMN rule_candidates.validation_status IS 'CANDIDATE, VALIDATED, REJECTED, IN_USE, DEPRECATED';
