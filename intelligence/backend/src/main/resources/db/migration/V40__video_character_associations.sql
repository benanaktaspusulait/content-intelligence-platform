CREATE TABLE character_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  UNIQUE(character_id, normalized_alias),
  UNIQUE(normalized_alias)
);

INSERT INTO character_aliases(id, character_id, alias, normalized_alias)
SELECT gen_random_uuid(), id, name, lower(name)
FROM characters
ON CONFLICT (normalized_alias) DO NOTHING;

ALTER TABLE video_characters
  ADD COLUMN association_source TEXT NOT NULL DEFAULT 'EXPLICIT_EXISTING_RELATION',
  ADD COLUMN confidence TEXT NOT NULL DEFAULT 'HIGH',
  ADD COLUMN source_prompt_path TEXT,
  ADD COLUMN resolver_version TEXT,
  ADD COLUMN evidence_reference TEXT,
  ADD COLUMN manually_confirmed BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE video_characters
  ADD CONSTRAINT video_characters_association_source_check
  CHECK (association_source IN ('PRODUCTION_CONTRACT','VIDEO_PLAN','EXPLICIT_EXISTING_RELATION','PROMPT_ENTITY','PROMPT_FILE','PROMPT_FILE_INFERRED','MANUAL','LEGACY_BACKFILL')),
  ADD CONSTRAINT video_characters_confidence_check
  CHECK (confidence IN ('HIGH','MEDIUM','LOW','UNKNOWN'));

CREATE INDEX idx_video_characters_character_role ON video_characters(character_id, participation, role);
CREATE INDEX idx_video_characters_source ON video_characters(association_source);

CREATE TABLE video_prompt_resolutions (
  video_id UUID PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('MATCHED_EXACT','MATCHED_SIDECAR','MATCHED_SINGLE_FOLDER_PROMPT','AMBIGUOUS','NOT_FOUND','ERROR')),
  prompt_path TEXT,
  matching_method TEXT,
  confidence TEXT NOT NULL CHECK (confidence IN ('HIGH','MEDIUM','LOW','UNKNOWN')),
  candidate_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  resolver_version TEXT NOT NULL,
  resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_video_prompt_resolutions_status ON video_prompt_resolutions(status);
