CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE series (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE videos (
  id UUID PRIMARY KEY,
  content_hash VARCHAR(64) NOT NULL UNIQUE,
  original_filename TEXT NOT NULL,
  relative_path TEXT NOT NULL UNIQUE,
  duration_ms BIGINT NOT NULL CHECK (duration_ms > 0),
  width INTEGER NOT NULL CHECK (width > 0),
  height INTEGER NOT NULL CHECK (height > 0),
  fps DOUBLE PRECISION NOT NULL CHECK (fps > 0),
  aspect_ratio DOUBLE PRECISION NOT NULL CHECK (aspect_ratio > 0),
  codec TEXT NOT NULL,
  audio_present BOOLEAN NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('INGESTED','ANALYSING','ANALYSED','READY','PUBLISHED','FAILED')),
  series_id UUID REFERENCES series(id),
  ingested_at TIMESTAMPTZ NOT NULL,
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_series ON videos(series_id);

CREATE TABLE video_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  parent_variant_id UUID REFERENCES video_variants(id),
  variant_type TEXT NOT NULL CHECK (variant_type IN ('ORIGINAL','HOOK_COLD_OPEN','TRIMMED','NO_CTA','LOOP_CUT','CUSTOM_EDIT')),
  generated_path TEXT NOT NULL UNIQUE,
  edit_operations JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE characters (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('NEW','UNTESTED','LIMITED_DATA','ESTABLISHED')),
  notes TEXT,
  active BOOLEAN NOT NULL DEFAULT true,
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE character_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  relative_path TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE video_characters (
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  participation TEXT NOT NULL CHECK (participation IN ('PRIMARY','SECONDARY')),
  role TEXT NOT NULL CHECK (role IN ('PROTAGONIST','HELPER','RIVAL','OBSERVER','COMEDIC_TARGET','TEACHER','UNKNOWN')),
  screen_time_ratio DOUBLE PRECISION,
  action_share DOUBLE PRECISION,
  speaking_share DOUBLE PRECISION,
  PRIMARY KEY (video_id, character_id)
);
CREATE UNIQUE INDEX idx_one_primary_character ON video_characters(video_id) WHERE participation='PRIMARY';

CREATE TABLE character_pairs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  first_character_id UUID NOT NULL REFERENCES characters(id),
  second_character_id UUID NOT NULL REFERENCES characters(id),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (first_character_id < second_character_id),
  UNIQUE(first_character_id,second_character_id)
);

CREATE TABLE creative_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_version TEXT NOT NULL,
  primary_engine TEXT NOT NULL,
  secondary_engines JSONB NOT NULL DEFAULT '[]',
  classification TEXT NOT NULL CHECK (classification IN ('BAD','AVERAGE_FIXABLE','GOOD','WINNER_CANDIDATE')),
  action_dna_score DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  reason TEXT NOT NULL,
  storyboard_path TEXT,
  timeline JSONB NOT NULL DEFAULT '[]',
  raw_result JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(video_id, analysis_version)
);

CREATE TABLE creative_fingerprints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  analysis_id UUID NOT NULL REFERENCES creative_analyses(id) ON DELETE CASCADE,
  feature_version TEXT NOT NULL,
  creative_quality_score DOUBLE PRECISION NOT NULL,
  features JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(video_id, feature_version)
);

CREATE TABLE creative_features (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id UUID NOT NULL REFERENCES creative_analyses(id) ON DELETE CASCADE,
  feature_name TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  evidence TEXT NOT NULL,
  timestamp_ranges JSONB NOT NULL DEFAULT '[]',
  UNIQUE(analysis_id,feature_name)
);

CREATE TABLE model_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version TEXT NOT NULL UNIQUE,
  model_type TEXT NOT NULL,
  platform TEXT NOT NULL,
  training_dataset_version TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  knowledge_cutoff TIMESTAMPTZ NOT NULL,
  metrics JSONB NOT NULL,
  artifact_path TEXT,
  status TEXT NOT NULL CHECK (status IN ('CHALLENGER','CHAMPION','RETIRED')),
  trained_at TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX idx_champion_platform_type ON model_versions(platform,model_type) WHERE status='CHAMPION';

CREATE TABLE model_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version_id UUID NOT NULL REFERENCES model_versions(id),
  platform TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  sample_size INTEGER NOT NULL,
  metrics JSONB NOT NULL,
  evaluation_method TEXT NOT NULL,
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE predictions (
  id UUID PRIMARY KEY,
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  variant_id UUID REFERENCES video_variants(id),
  platform TEXT NOT NULL,
  prediction_type TEXT NOT NULL CHECK (prediction_type IN ('PRE_PUBLISH','LIVE')),
  status TEXT NOT NULL CHECK (status IN ('DRAFT','LOCKED','EVALUATED')),
  model_version TEXT NOT NULL,
  dataset_version TEXT NOT NULL,
  feature_version TEXT NOT NULL,
  knowledge_cutoff TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  confidence TEXT NOT NULL,
  comparable_sample_size INTEGER NOT NULL,
  locked_at TIMESTAMPTZ,
  lock_reason TEXT,
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_predictions_video_platform ON predictions(video_id,platform,created_at DESC);

CREATE TABLE human_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id),
  platform TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  expected_value DOUBLE PRECISION,
  performance_band TEXT,
  rationale TEXT,
  blinded BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE prediction_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id UUID NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  horizon_minutes INTEGER NOT NULL,
  metric TEXT NOT NULL,
  expected_value DOUBLE PRECISION,
  interval_50_low DOUBLE PRECISION,
  interval_50_high DOUBLE PRECISION,
  interval_80_low DOUBLE PRECISION,
  interval_80_high DOUBLE PRECISION,
  interval_90_low DOUBLE PRECISION,
  interval_90_high DOUBLE PRECISION,
  probabilities JSONB NOT NULL DEFAULT '{}',
  UNIQUE(prediction_id,horizon_minutes,metric)
);

CREATE OR REPLACE FUNCTION prevent_locked_prediction_mutation() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('LOCKED','EVALUATED') THEN
    IF TG_OP = 'UPDATE'
       AND OLD.status = 'LOCKED'
       AND NEW.status = 'EVALUATED'
       AND (to_jsonb(NEW) - ARRAY['status','updated_at','entity_version'])
           = (to_jsonb(OLD) - ARRAY['status','updated_at','entity_version']) THEN
      RETURN NEW;
    END IF;
    RAISE EXCEPTION 'Locked prediction % is immutable', OLD.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER predictions_immutable BEFORE UPDATE OR DELETE ON predictions
FOR EACH ROW EXECUTE FUNCTION prevent_locked_prediction_mutation();

CREATE OR REPLACE FUNCTION prevent_locked_target_mutation() RETURNS trigger AS $$
DECLARE prediction_status TEXT;
BEGIN
  SELECT status INTO prediction_status
  FROM predictions
  WHERE id=CASE WHEN TG_OP='DELETE' THEN OLD.prediction_id ELSE NEW.prediction_id END;
  IF prediction_status IN ('LOCKED','EVALUATED') THEN
    RAISE EXCEPTION 'Locked prediction targets are immutable';
  END IF;
  RETURN COALESCE(NEW,OLD);
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER prediction_targets_immutable BEFORE INSERT OR UPDATE OR DELETE ON prediction_targets
FOR EACH ROW EXECUTE FUNCTION prevent_locked_target_mutation();

CREATE TABLE experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id),
  variant_id UUID REFERENCES video_variants(id),
  platform TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  experiment_type TEXT NOT NULL CHECK (experiment_type IN ('EXPLOIT','ADJACENT','EXPLORE','CHARACTER_CONTROL_TEST')),
  planned_publish_time TIMESTAMPTZ,
  actual_publish_time TIMESTAMPTZ,
  test_variables JSONB NOT NULL DEFAULT '{}',
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'PLANNED',
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE experiment_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
  video_variant_id UUID REFERENCES video_variants(id),
  label TEXT NOT NULL,
  allocation_percentage DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE human_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID REFERENCES experiments(id),
  video_id UUID NOT NULL REFERENCES videos(id),
  decision TEXT NOT NULL,
  reason TEXT,
  decided_by TEXT NOT NULL,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_filename TEXT NOT NULL,
  source_hash VARCHAR(64) NOT NULL UNIQUE,
  platform TEXT,
  parser_version TEXT NOT NULL,
  timezone_assumption TEXT NOT NULL,
  column_mapping JSONB NOT NULL,
  quality_report JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_rows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_batch_id UUID NOT NULL REFERENCES import_batches(id),
  sheet_name TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_data JSONB NOT NULL,
  matched_video_id UUID REFERENCES videos(id),
  match_status TEXT NOT NULL,
  match_confidence DOUBLE PRECISION,
  UNIQUE(import_batch_id,sheet_name,source_row_number)
);

CREATE TABLE performance_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_row_id UUID NOT NULL UNIQUE REFERENCES import_rows(id),
  video_id UUID REFERENCES videos(id),
  variant_id UUID REFERENCES video_variants(id),
  platform TEXT NOT NULL,
  platform_content_id TEXT,
  publication_timestamp TIMESTAMPTZ,
  measurement_timestamp TIMESTAMPTZ,
  metric_semantics TEXT NOT NULL CHECK (metric_semantics IN ('DAILY_INCREMENT','CUMULATIVE','SNAPSHOT','UNKNOWN')),
  views BIGINT, reach BIGINT, unique_viewers BIGINT,
  three_second_views BIGINT, fifteen_second_views BIGINT,
  average_watch_seconds DOUBLE PRECISION, total_watch_seconds DOUBLE PRECISION,
  likes BIGINT, comments BIGINT, shares BIGINT, saves BIGINT, follows BIGINT,
  recommendation_percentage DOUBLE PRECISION,
  followers_percentage DOUBLE PRECISION,
  nonfollowers_percentage DOUBLE PRECISION,
  paid BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_performance_video_time ON performance_observations(video_id,platform,measurement_timestamp);

CREATE TABLE country_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  performance_observation_id UUID NOT NULL REFERENCES performance_observations(id) ON DELETE CASCADE,
  country_code CHAR(2) NOT NULL,
  percentage DOUBLE PRECISION NOT NULL,
  estimated_absolute_count BIGINT,
  denominator_metric TEXT
);

CREATE TABLE import_conflicts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  import_row_id UUID NOT NULL REFERENCES import_rows(id),
  existing_observation_id UUID REFERENCES performance_observations(id),
  metric TEXT NOT NULL,
  existing_value TEXT,
  incoming_value TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN',
  resolution TEXT,
  resolved_at TIMESTAMPTZ
);

CREATE TABLE analysis_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id),
  job_type TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')),
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 3,
  request_payload JSONB NOT NULL DEFAULT '{}',
  result_payload JSONB,
  error_message TEXT,
  available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_claim ON analysis_jobs(state,available_at);

CREATE TABLE prediction_audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id UUID NOT NULL REFERENCES predictions(id),
  horizon_minutes INTEGER NOT NULL,
  actual_value DOUBLE PRECISION,
  absolute_error DOUBLE PRECISION,
  log_error DOUBLE PRECISION,
  band_correct BOOLEAN,
  interval_50_covered BOOLEAN,
  interval_80_covered BOOLEAN,
  brier_score DOUBLE PRECISION,
  trajectory_correct BOOLEAN,
  surprise_score DOUBLE PRECISION,
  audit_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(prediction_id,horizon_minutes)
);

CREATE TABLE research_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  observation TEXT NOT NULL,
  date_from DATE,
  date_to DATE,
  platform TEXT,
  sample_size INTEGER NOT NULL,
  effect_size DOUBLE PRECISION,
  confidence TEXT NOT NULL,
  limitations TEXT NOT NULL,
  evidence JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE intervention_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id),
  platform TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_time TIMESTAMPTZ NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  reason TEXT,
  old_state JSONB,
  new_state JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
