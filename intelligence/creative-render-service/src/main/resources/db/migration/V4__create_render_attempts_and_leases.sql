-- V4: Persistent render attempts, leasing, and worker claim (Slice B Task 3).
--
-- Replaces the previous single-long-transaction, recursive-rerender orchestration with durable,
-- per-attempt execution state safe for multiple concurrent worker processes. A job's attempts are
-- an append-only sequence (attempt_number starting at 1, unique per render_job_id): a rerender
-- inserts attempt N+1 rather than mutating an existing row, so a job's full execution history is
-- always reconstructable. A worker claims an attempt by acquiring its lease, executes exactly the
-- attempt's current stage, and persists the next stage before releasing or renewing the lease.

CREATE TABLE render_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    render_job_id UUID NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL CHECK (attempt_number >= 1),

    stage VARCHAR(30) NOT NULL CHECK (
        stage IN (
            'QUEUED', 'SUBMITTING', 'PROVIDER_QUEUED', 'POLLING', 'DOWNLOADING',
            'POST_RENDER_QA', 'RETRY_WAIT', 'COMPLETE', 'FAILED', 'ABANDONED',
            'NEEDS_HUMAN_REVIEW'
        )
    ),

    provider_job_id VARCHAR(100),
    provider_job_state VARCHAR(20) CHECK (
        provider_job_state IS NULL OR provider_job_state IN (
            'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'UNKNOWN'
        )
    ),

    -- The RenderAsset recorded by the DOWNLOADING stage, read back by POST_RENDER_QA on a later
    -- (possibly different-process) claim of the same attempt. NULL until DOWNLOADING completes.
    asset_id UUID REFERENCES render_assets(id),

    poll_count INT NOT NULL DEFAULT 0 CHECK (poll_count >= 0),
    next_poll_at TIMESTAMPTZ,
    eligible_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Lease: a worker holds a claimed attempt exclusively until lease_expires_at. A worker that
    -- dies mid-attempt leaves a lease that simply expires - RenderAttemptClaimRepository's claim
    -- query treats any attempt whose lease_expires_at has passed as eligible again, so recovery
    -- requires no explicit crash detection.
    lease_owner VARCHAR(100),
    lease_expires_at TIMESTAMPTZ,
    lease_heartbeat_at TIMESTAMPTZ,

    error_code VARCHAR(50),
    error_message TEXT,
    terminal_reason TEXT,

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 0,

    CONSTRAINT uq_render_attempts_job_attempt_number UNIQUE (render_job_id, attempt_number)
);

-- The claim query (RenderAttemptClaimRepository) filters on: no active lease, due poll/retry time,
-- and non-terminal stage. These two indexes cover that filter without a full table scan as the
-- table grows.
CREATE INDEX idx_render_attempts_claim_eligibility
    ON render_attempts(stage, eligible_at, next_poll_at, lease_expires_at);

CREATE INDEX idx_render_attempts_render_job_id ON render_attempts(render_job_id);

COMMENT ON TABLE render_attempts IS
  'Durable, append-only per-attempt execution state for render_jobs. One row per attempt (never mutated into a different attempt_number); a worker claims a row via the lease_* columns and advances it exactly one stage per claim.';
COMMENT ON COLUMN render_attempts.attempt_number IS
  'Append-only sequence starting at 1, unique per render_job_id. A rerender inserts attempt_number+1; existing rows are never renumbered.';
COMMENT ON COLUMN render_attempts.lease_expires_at IS
  'A claimed attempt is exclusively owned by lease_owner until this time. An attempt whose lease has expired (or who has none) and is otherwise eligible can be claimed by any worker - this is what makes a crashed worker''s in-flight attempts recoverable without explicit crash detection.';
