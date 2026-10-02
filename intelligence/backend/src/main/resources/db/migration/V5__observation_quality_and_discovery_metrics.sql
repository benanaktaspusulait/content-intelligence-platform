ALTER TABLE performance_observations ALTER COLUMN import_row_id DROP NOT NULL;

ALTER TABLE performance_observations
  ADD COLUMN plays BIGINT,
  ADD COLUMN completion_rate DOUBLE PRECISION,
  ADD COLUMN skip_rate DOUBLE PRECISION,
  ADD COLUMN profile_visits BIGINT,
  ADD COLUMN follows_attributed BIGINT,
  ADD COLUMN source TEXT NOT NULL DEFAULT 'CSV',
  ADD COLUMN source_version TEXT NOT NULL DEFAULT 'performance-import-v1',
  ADD COLUMN source_observation_key TEXT,
  ADD COLUMN raw_payload_json JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN collection_latency_ms BIGINT,
  ADD COLUMN data_quality_status TEXT NOT NULL DEFAULT 'IMPORTED';

ALTER TABLE performance_observations
  ADD CONSTRAINT performance_observation_quality_check
    CHECK (data_quality_status IN ('EXACT','API_REPORTED','IMPORTED','MANUAL','ESTIMATED','INTERPOLATED','UNAVAILABLE')),
  ADD CONSTRAINT performance_follower_percentage_check
    CHECK (followers_percentage IS NULL OR followers_percentage BETWEEN 0 AND 100),
  ADD CONSTRAINT performance_nonfollower_percentage_check
    CHECK (nonfollowers_percentage IS NULL OR nonfollowers_percentage BETWEEN 0 AND 100),
  ADD CONSTRAINT performance_completion_rate_check
    CHECK (completion_rate IS NULL OR completion_rate BETWEEN 0 AND 100),
  ADD CONSTRAINT performance_skip_rate_check
    CHECK (skip_rate IS NULL OR skip_rate BETWEEN 0 AND 100);

CREATE UNIQUE INDEX uq_performance_source_observation
  ON performance_observations(platform, source, source_observation_key)
  WHERE source_observation_key IS NOT NULL;

ALTER TABLE country_observations
  ADD COLUMN observed_at TIMESTAMPTZ,
  ADD COLUMN source TEXT NOT NULL DEFAULT 'CSV',
  ADD COLUMN data_quality_status TEXT NOT NULL DEFAULT 'IMPORTED';

ALTER TABLE country_observations
  ADD CONSTRAINT country_observation_quality_check
    CHECK (data_quality_status IN ('EXACT','API_REPORTED','IMPORTED','MANUAL','ESTIMATED','INTERPOLATED','UNAVAILABLE')),
  ADD CONSTRAINT country_percentage_check CHECK (percentage BETWEEN 0 AND 100);

CREATE UNIQUE INDEX uq_country_observation_per_snapshot
  ON country_observations(performance_observation_id, country_code);

CREATE TABLE derived_performance_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  performance_observation_id UUID NOT NULL REFERENCES performance_observations(id) ON DELETE CASCADE,
  metric_name TEXT NOT NULL,
  metric_value DOUBLE PRECISION,
  algorithm_version TEXT NOT NULL,
  components JSONB NOT NULL DEFAULT '{}',
  data_quality_status TEXT NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(performance_observation_id, metric_name, algorithm_version),
  CHECK (data_quality_status IN ('EXACT','API_REPORTED','IMPORTED','MANUAL','ESTIMATED','INTERPOLATED','UNAVAILABLE'))
);

CREATE OR REPLACE FUNCTION prevent_observation_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER performance_observations_append_only
BEFORE UPDATE OR DELETE ON performance_observations
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();

CREATE TRIGGER country_observations_append_only
BEFORE UPDATE OR DELETE ON country_observations
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();

CREATE TRIGGER derived_performance_metrics_append_only
BEFORE UPDATE OR DELETE ON derived_performance_metrics
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
