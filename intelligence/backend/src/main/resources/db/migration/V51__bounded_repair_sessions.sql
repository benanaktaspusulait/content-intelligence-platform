CREATE TABLE workflow_repair_sessions (
 id UUID PRIMARY KEY,
 review_id UUID NOT NULL REFERENCES post_family_workflow_events(id),
 idempotency_key TEXT NOT NULL,
 state TEXT NOT NULL CHECK (state IN ('READY','RUNNING','STOPPED','CANCELLED','ACCEPTED','REJECTED')),
 max_attempts INT NOT NULL CHECK (max_attempts BETWEEN 1 AND 2),
 attempts INT NOT NULL DEFAULT 0,
 max_cost_usd NUMERIC NOT NULL CHECK (max_cost_usd > 0),
 reserved_cost_usd NUMERIC NOT NULL DEFAULT 0,
 payload JSONB NOT NULL DEFAULT '{}',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(review_id,idempotency_key)
);

CREATE UNIQUE INDEX workflow_repair_sessions_one_active_source ON workflow_repair_sessions(review_id) WHERE state IN ('READY','RUNNING');
