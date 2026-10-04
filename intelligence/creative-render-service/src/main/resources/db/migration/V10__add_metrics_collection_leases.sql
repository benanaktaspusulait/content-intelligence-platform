ALTER TABLE metrics_collection_jobs
  ADD COLUMN lease_owner VARCHAR(100),
  ADD COLUMN lease_expires_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_metrics_collection_claim
  ON metrics_collection_jobs(status, scheduled_at, lease_expires_at);
