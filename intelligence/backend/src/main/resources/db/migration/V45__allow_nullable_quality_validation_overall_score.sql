-- Family 9 permits unevaluable reports and scores with up to six decimal places.
-- The legacy statistics view depends on the column type, so recreate it around the type change.
DROP VIEW IF EXISTS quality_validation_stats;
DROP VIEW IF EXISTS recent_validation_failures;

ALTER TABLE quality_validations
  ALTER COLUMN overall_score TYPE NUMERIC(12,6)
    USING overall_score::NUMERIC(12,6),
  ALTER COLUMN overall_score DROP NOT NULL;

CREATE VIEW quality_validation_stats AS
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

CREATE VIEW recent_validation_failures AS
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
