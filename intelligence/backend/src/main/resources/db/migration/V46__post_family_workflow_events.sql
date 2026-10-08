-- Separately versioned append-only operational evidence; frozen records are untouched.
CREATE TABLE post_family_workflow_events (
  id UUID PRIMARY KEY,
  kind VARCHAR(40) NOT NULL,
  binding_sha256 VARCHAR(64),
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX post_family_workflow_events_kind_time ON post_family_workflow_events(kind,created_at DESC);
