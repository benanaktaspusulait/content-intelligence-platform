CREATE TABLE publication_attempts (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    stage VARCHAR(30) NOT NULL,
    eligible_at TIMESTAMP WITH TIME ZONE NOT NULL,
    lease_owner VARCHAR(100),
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    provider_submission_id VARCHAR(200),
    platform_post_id VARCHAR(200),
    platform_video_id VARCHAR(200),
    authoritative_permalink TEXT,
    error_code VARCHAR(80),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    entity_version INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_publication_attempt_job_number UNIQUE(publication_job_id, attempt_number)
);

CREATE INDEX idx_publication_attempt_claim
  ON publication_attempts(stage, eligible_at, lease_expires_at);

ALTER TABLE scheduled_publications
  ADD COLUMN schedule_status VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
  ADD COLUMN lease_owner VARCHAR(100),
  ADD COLUMN lease_expires_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN original_local_time TIMESTAMP,
  ADD COLUMN cancellation_requested_at TIMESTAMP WITH TIME ZONE;

UPDATE scheduled_publications
SET schedule_status = CASE WHEN is_executed THEN 'ENQUEUED' ELSE 'SCHEDULED' END;

CREATE INDEX idx_scheduled_publication_claim
  ON scheduled_publications(schedule_status, scheduled_at, lease_expires_at);
