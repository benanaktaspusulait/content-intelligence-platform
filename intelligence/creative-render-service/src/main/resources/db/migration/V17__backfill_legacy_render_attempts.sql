-- Legacy render_jobs were copied before durable render_attempts existed. Backfill one attempt so
-- queued/active jobs are visible to the worker and completed/failed jobs retain retry history.
INSERT INTO render_attempts (
    id,
    render_job_id,
    attempt_number,
    stage,
    provider_job_id,
    provider_job_state,
    poll_count,
    eligible_at,
    error_code,
    error_message,
    started_at,
    completed_at,
    created_at,
    updated_at,
    entity_version
)
SELECT
    gen_random_uuid(),
    job.id,
    GREATEST(COALESCE(job.attempt_number, 1), 1),
    CASE job.status
        WHEN 'COMPLETE' THEN 'COMPLETE'
        WHEN 'FAILED' THEN 'FAILED'
        WHEN 'ABANDONED' THEN 'ABANDONED'
        WHEN 'DOWNLOADING' THEN CASE
            WHEN job.openart_job_id IS NULL THEN 'FAILED'
            ELSE 'DOWNLOADING'
        END
        WHEN 'GENERATING' THEN CASE
            WHEN job.openart_job_id IS NULL THEN 'QUEUED'
            ELSE 'PROVIDER_QUEUED'
        END
        WHEN 'POLLING' THEN CASE
            WHEN job.openart_job_id IS NULL THEN 'QUEUED'
            ELSE 'PROVIDER_QUEUED'
        END
        ELSE 'QUEUED'
    END,
    job.openart_job_id,
    CASE
        WHEN job.status = 'COMPLETE' AND job.openart_job_id IS NOT NULL THEN 'SUCCEEDED'
        WHEN job.openart_job_id IS NOT NULL THEN 'UNKNOWN'
        ELSE NULL
    END,
    0,
    NOW(),
    job.error_code,
    job.error_message,
    job.started_at,
    CASE
        WHEN job.status IN ('COMPLETE', 'FAILED', 'ABANDONED') THEN COALESCE(job.completed_at, job.failed_at)
        ELSE NULL
    END,
    COALESCE(job.created_at, NOW()),
    COALESCE(job.updated_at, NOW()),
    0
FROM render_jobs job
WHERE NOT EXISTS (
    SELECT 1
    FROM render_attempts attempt
    WHERE attempt.render_job_id = job.id
);
