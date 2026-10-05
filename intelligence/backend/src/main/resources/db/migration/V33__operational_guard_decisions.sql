CREATE TABLE operational_guard_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  guard_type TEXT NOT NULL CHECK (guard_type IN ('DISTRIBUTION','RETENTION')),
  platform TEXT NOT NULL,
  scope_type TEXT NOT NULL DEFAULT 'PLATFORM' CHECK (scope_type IN ('PLATFORM')),
  state TEXT NOT NULL CHECK (state IN (
    'HEALTHY','WATCH','PUBLICATION_REVIEW_REQUIRED','WEAK_RETENTION','CREATIVE_REVIEW_REQUIRED',
    'INSUFFICIENT_EVIDENCE')),
  policy_version TEXT NOT NULL,
  evidence_count INTEGER NOT NULL DEFAULT 0,
  metric_value DOUBLE PRECISION,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  evidence JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_operational_guard_latest
  ON operational_guard_decisions(guard_type, platform, evaluated_at DESC);

CREATE TRIGGER operational_guard_decisions_append_only
BEFORE UPDATE OR DELETE ON operational_guard_decisions
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();

COMMENT ON TABLE operational_guard_decisions IS
  'Append-only descriptive operational health decisions; never a render or asset gate.';
