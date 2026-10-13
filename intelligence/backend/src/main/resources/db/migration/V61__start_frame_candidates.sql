-- Start-frame candidate images for render preparation
CREATE TABLE IF NOT EXISTS start_frame_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id INTEGER NOT NULL,
  prompt_version_id INTEGER NOT NULL,
  candidate_id TEXT NOT NULL,
  character_id UUID NOT NULL,
  reference_id UUID NOT NULL,
  reference_sha256 TEXT NOT NULL,
  image_path TEXT NOT NULL,
  image_sha256 TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  model TEXT NOT NULL,
  quality TEXT NOT NULL DEFAULT 'medium',
  cost_usd NUMERIC(10,4) NOT NULL DEFAULT 0.053,
  status TEXT NOT NULL DEFAULT 'CANDIDATE',
  rejected_at TIMESTAMPTZ,
  rejected_by TEXT,
  rejected_reason TEXT,
  accepted_at TIMESTAMPTZ,
  accepted_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT valid_status CHECK (status IN ('CANDIDATE', 'ACCEPTED', 'REJECTED')),
  CONSTRAINT positive_dimensions CHECK (width > 0 AND height > 0)
);

CREATE INDEX IF NOT EXISTS idx_start_frame_content ON start_frame_candidates(content_id, prompt_version_id);
CREATE INDEX IF NOT EXISTS idx_start_frame_status ON start_frame_candidates(content_id, status);

-- Only one accepted start frame per content/prompt version
CREATE UNIQUE INDEX IF NOT EXISTS uq_accepted_start_frame
  ON start_frame_candidates(content_id, prompt_version_id)
  WHERE status = 'ACCEPTED';
