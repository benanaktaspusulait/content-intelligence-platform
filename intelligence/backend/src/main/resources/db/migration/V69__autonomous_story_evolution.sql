CREATE TABLE IF NOT EXISTS story_evolution_runs (
 id UUID PRIMARY KEY,
 owner_principal TEXT NOT NULL,
 idempotency_key TEXT NOT NULL,
 source_story_record_id UUID NOT NULL,
 source_story_sha256 TEXT NOT NULL,
 authorization_payload JSONB NOT NULL,
 scope JSONB NOT NULL,
 state TEXT NOT NULL,
 progress JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 deadline TIMESTAMPTZ NOT NULL,
 cancel_requested BOOLEAN NOT NULL DEFAULT false,
 UNIQUE(owner_principal,idempotency_key)
);
CREATE TABLE IF NOT EXISTS story_evolution_drafts (
 id UUID PRIMARY KEY,
 run_id UUID NOT NULL REFERENCES story_evolution_runs(id),
 round_number INTEGER NOT NULL,
 parent_draft_id UUID NULL,
 candidate_id TEXT NOT NULL,
 prompt_payload JSONB NOT NULL,
 candidate_sha256 TEXT NOT NULL,
 assessment JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(run_id,round_number,candidate_id)
);
CREATE TABLE IF NOT EXISTS story_evolution_events (
 id UUID PRIMARY KEY,
 run_id UUID NOT NULL REFERENCES story_evolution_runs(id),
 payload JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS story_evolution_runs_owner_idx ON story_evolution_runs(owner_principal,created_at DESC);
