CREATE SCHEMA IF NOT EXISTS publisher_support;

CREATE TABLE publisher_support.provider_operation_records (
    id UUID PRIMARY KEY,
    publication_job_id UUID NOT NULL,
    publication_attempt_id UUID NOT NULL,
    command_idempotency_key VARCHAR(200) NOT NULL,
    command_fingerprint VARCHAR(64) NOT NULL,
    provider_request_id VARCHAR(200),
    status VARCHAR(40),
    provider_post_id VARCHAR(200),
    provider_video_id VARCHAR(200),
    permalink TEXT,
    error_class VARCHAR(50),
    message TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    reconciliation_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    entity_version INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_provider_operation_command_idempotency_key
      UNIQUE(command_idempotency_key)
);

CREATE INDEX idx_provider_operation_reconciliation
  ON publisher_support.provider_operation_records(reconciliation_required, status);

CREATE INDEX idx_provider_operation_provider_request
  ON publisher_support.provider_operation_records(provider_request_id);
