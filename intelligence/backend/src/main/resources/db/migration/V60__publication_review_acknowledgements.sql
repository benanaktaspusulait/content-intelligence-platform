-- Phase 6: Publication review acknowledgement record.
-- Stores operator acknowledgement when a guard signal (e.g. PUBLICATION_REVIEW_REQUIRED)
-- is reviewed before the next publication attempt. This is a descriptive signal only;
-- it does not block rendering or publication execution.

CREATE TABLE publication_review_acknowledgements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL,
  guard_decision_id UUID NOT NULL REFERENCES operational_guard_decisions(id),
  acknowledged_by TEXT NOT NULL,
  acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT,
  UNIQUE(platform, guard_decision_id)
);

CREATE INDEX idx_publication_review_ack_platform
  ON publication_review_acknowledgements(platform, acknowledged_at DESC);

COMMENT ON TABLE publication_review_acknowledgements IS
  'Append-only operator acknowledgement of operational guard signals; never a render or publication block.';
