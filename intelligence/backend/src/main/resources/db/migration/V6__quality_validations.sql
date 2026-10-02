-- Pompom Creative Quality Engine: Validation History
-- Stores quality validation results for video prompts

CREATE TABLE quality_validations (
    id BIGSERIAL PRIMARY KEY,
    
    -- Prompt reference (optional FK to video prompts table if exists)
    prompt_id BIGINT,
    
    -- Prompt content
    prompt_text TEXT NOT NULL,
    
    -- Validation metadata
    ruleset_version VARCHAR(10) NOT NULL,
    
    -- Quality scores
    overall_score NUMERIC(5,2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('RENDER_READY', 'NEEDS_REVISION', 'BLOCKED')),
    
    -- Rule failure counts
    blocker_count INT NOT NULL DEFAULT 0 CHECK (blocker_count >= 0),
    critical_count INT NOT NULL DEFAULT 0 CHECK (critical_count >= 0),
    warning_count INT NOT NULL DEFAULT 0 CHECK (warning_count >= 0),
    
    -- Failed rules (comma-separated rule IDs for quick reference)
    failed_rules TEXT,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_quality_validations_prompt_id ON quality_validations(prompt_id) WHERE prompt_id IS NOT NULL;
CREATE INDEX idx_quality_validations_status ON quality_validations(status);
CREATE INDEX idx_quality_validations_ruleset_version ON quality_validations(ruleset_version);
CREATE INDEX idx_quality_validations_created_at ON quality_validations(created_at DESC);
CREATE INDEX idx_quality_validations_score ON quality_validations(overall_score);

-- Composite index for analytics queries
CREATE INDEX idx_quality_validations_status_score ON quality_validations(status, overall_score);

-- Comments
COMMENT ON TABLE quality_validations IS 'Validation history for Pompom Creative Quality Engine';
COMMENT ON COLUMN quality_validations.prompt_id IS 'Optional FK to video prompts table';
COMMENT ON COLUMN quality_validations.prompt_text IS 'Full prompt text validated';
COMMENT ON COLUMN quality_validations.ruleset_version IS 'Ruleset version used (e.g., 1.0, 1.1)';
COMMENT ON COLUMN quality_validations.overall_score IS 'Quality score 0-100';
COMMENT ON COLUMN quality_validations.status IS 'RENDER_READY (92+ score, zero blockers/criticals), NEEDS_REVISION (80-91 score), BLOCKED (<80 score or blockers)';
COMMENT ON COLUMN quality_validations.blocker_count IS 'Number of BLOCKER-level rule failures (must be 0 for RENDER_READY)';
COMMENT ON COLUMN quality_validations.critical_count IS 'Number of CRITICAL-level rule failures (must be 0 for RENDER_READY)';
COMMENT ON COLUMN quality_validations.warning_count IS 'Number of WARNING-level issues';
COMMENT ON COLUMN quality_validations.failed_rules IS 'Comma-separated failed rule IDs (e.g., CONCEPT_006,BEAT_004)';

-- Create view for validation statistics
CREATE OR REPLACE VIEW quality_validation_stats AS
SELECT
    ruleset_version,
    COUNT(*) AS total_validations,
    COUNT(*) FILTER (WHERE status = 'RENDER_READY') AS render_ready_count,
    COUNT(*) FILTER (WHERE status = 'NEEDS_REVISION') AS needs_revision_count,
    COUNT(*) FILTER (WHERE status = 'BLOCKED') AS blocked_count,
    ROUND(CAST(AVG(overall_score) AS numeric), 2) AS avg_score,
    ROUND(CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY overall_score) AS numeric), 2) AS median_score,
    MIN(overall_score) AS min_score,
    MAX(overall_score) AS max_score,
    MIN(created_at) AS first_validation,
    MAX(created_at) AS last_validation
FROM quality_validations
GROUP BY ruleset_version
ORDER BY ruleset_version DESC;

COMMENT ON VIEW quality_validation_stats IS 'Aggregated validation statistics per ruleset version';

-- Create view for recent validation failures
CREATE OR REPLACE VIEW recent_validation_failures AS
SELECT
    id,
    prompt_id,
    LEFT(prompt_text, 100) || '...' AS prompt_preview,
    ruleset_version,
    overall_score,
    status,
    blocker_count,
    critical_count,
    warning_count,
    failed_rules,
    created_at
FROM quality_validations
WHERE status IN ('BLOCKED', 'NEEDS_REVISION')
ORDER BY created_at DESC
LIMIT 100;

COMMENT ON VIEW recent_validation_failures IS 'Last 100 prompts that did not pass validation';

-- Sample query examples (commented out, for documentation)
/*
-- Get validation history for a specific prompt
SELECT * FROM quality_validations 
WHERE prompt_id = 123 
ORDER BY created_at DESC;

-- Get average score by ruleset version
SELECT ruleset_version, AVG(overall_score) AS avg_score, COUNT(*) AS count
FROM quality_validations
GROUP BY ruleset_version
ORDER BY ruleset_version DESC;

-- Find prompts that improved after revision
WITH validation_pairs AS (
    SELECT 
        prompt_id,
        overall_score,
        created_at,
        LAG(overall_score) OVER (PARTITION BY prompt_id ORDER BY created_at) AS prev_score
    FROM quality_validations
    WHERE prompt_id IS NOT NULL
)
SELECT 
    prompt_id,
    prev_score,
    overall_score,
    (overall_score - prev_score) AS improvement
FROM validation_pairs
WHERE prev_score IS NOT NULL AND (overall_score - prev_score) > 10
ORDER BY improvement DESC;

-- Get most common failed rules
SELECT 
    UNNEST(string_to_array(failed_rules, ',')) AS rule_id,
    COUNT(*) AS failure_count
FROM quality_validations
WHERE failed_rules IS NOT NULL AND failed_rules != ''
GROUP BY rule_id
ORDER BY failure_count DESC
LIMIT 20;

-- Quality trend over time (last 30 days)
SELECT 
    DATE(created_at) AS validation_date,
    COUNT(*) AS total_validations,
    AVG(overall_score) AS avg_score,
    COUNT(*) FILTER (WHERE status = 'RENDER_READY') AS render_ready,
    COUNT(*) FILTER (WHERE status = 'BLOCKED') AS blocked
FROM quality_validations
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY validation_date DESC;
*/
