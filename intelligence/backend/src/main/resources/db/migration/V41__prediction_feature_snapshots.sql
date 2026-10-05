CREATE TABLE prediction_feature_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id UUID REFERENCES video_variants(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  feature_schema_version TEXT NOT NULL,
  source_analysis_version TEXT,
  semantic_schema_version TEXT,
  knowledge_cutoff TIMESTAMPTZ NOT NULL,
  features JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_prediction_feature_snapshots_video_platform
  ON prediction_feature_snapshots(video_id, platform, created_at DESC);

COMMENT ON TABLE prediction_feature_snapshots IS
  'Immutable pre-publish creative features. Performance outcomes must never be stored here.';
