CREATE TABLE video_publications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id UUID REFERENCES video_variants(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  publication_timezone TEXT NOT NULL,
  off_peak_publish BOOLEAN,
  context_label TEXT,
  source TEXT NOT NULL CHECK (source IN ('MANUAL','CSV','API','UI_OBSERVATION')),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_video_publication_context
  ON video_publications(video_id,COALESCE(variant_id,'00000000-0000-0000-0000-000000000000'::uuid),platform);

CREATE TABLE platform_content_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id UUID REFERENCES video_variants(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  state_type TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_platform_content_state
  ON platform_content_states(video_id,COALESCE(variant_id,'00000000-0000-0000-0000-000000000000'::uuid),platform,state_type);

CREATE TABLE platform_content_state_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  state_id UUID NOT NULL REFERENCES platform_content_states(id) ON DELETE CASCADE,
  state_value TEXT NOT NULL CHECK (state_value IN ('ACTIVE','INACTIVE','UNKNOWN')),
  observed_at TIMESTAMPTZ,
  source TEXT NOT NULL CHECK (source IN ('SCREENSHOT','MANUAL','CSV','API','UI_OBSERVATION')),
  source_import_id UUID REFERENCES import_batches(id),
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  notes TEXT,
  evidence_relative_path TEXT,
  ocr_result TEXT,
  manually_verified BOOLEAN NOT NULL DEFAULT false,
  correction_of_id UUID REFERENCES platform_content_state_observations(id),
  recorded_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (correction_of_id IS NULL OR correction_of_id <> id)
);
CREATE INDEX idx_platform_state_observation_timeline
  ON platform_content_state_observations(state_id,observed_at,created_at);
CREATE UNIQUE INDEX uq_platform_state_observation_known
  ON platform_content_state_observations(state_id,state_value,observed_at,source)
  WHERE observed_at IS NOT NULL AND correction_of_id IS NULL;

CREATE OR REPLACE FUNCTION prevent_platform_state_observation_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Platform state observations are append-only; create a correction observation';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER platform_state_observations_immutable
BEFORE UPDATE OR DELETE ON platform_content_state_observations
FOR EACH ROW EXECUTE FUNCTION prevent_platform_state_observation_mutation();

COMMENT ON TABLE platform_content_state_observations IS
  'Observed platform UI/API evidence. Presence does not establish causality or platform algorithm meaning.';
