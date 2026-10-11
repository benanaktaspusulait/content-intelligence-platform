ALTER TABLE character_references
  ADD COLUMN sha256 VARCHAR(64),
  ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'
    CHECK (approval_status IN ('PENDING_REVIEW','APPROVED','REJECTED')),
  ADD COLUMN approved_at TIMESTAMPTZ,
  ADD COLUMN approved_by TEXT,
  ADD COLUMN version_number INTEGER NOT NULL DEFAULT 1 CHECK (version_number > 0);

CREATE INDEX idx_character_references_review
  ON character_references(character_id, approval_status, created_at DESC);
