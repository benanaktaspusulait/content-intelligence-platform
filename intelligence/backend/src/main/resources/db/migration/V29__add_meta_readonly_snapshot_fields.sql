-- Meta read-only analytics snapshots.
-- Extends append-only performance_observations with Graph API availability and
-- sanitized error metadata, and video_publications with deterministic identity
-- match provenance. No publishing surface is introduced by these columns.

ALTER TABLE performance_observations
  ADD COLUMN total_interactions BIGINT,
  ADD COLUMN metric_availability_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED',
  ADD COLUMN insights_unavailable_reason TEXT,
  ADD COLUMN source_error_code INTEGER,
  ADD COLUMN source_error_subcode INTEGER,
  ADD COLUMN source_error_type TEXT,
  ADD COLUMN collection_run_id UUID;

ALTER TABLE performance_observations
  ADD CONSTRAINT performance_metric_availability_check
    CHECK (metric_availability_status IN ('NOT_REQUESTED','AVAILABLE','PARTIAL','UNAVAILABLE'));

CREATE INDEX idx_performance_platform_content_timeline
  ON performance_observations(platform, platform_content_id, measurement_timestamp DESC)
  WHERE platform_content_id IS NOT NULL;

COMMENT ON COLUMN performance_observations.metric_availability_status IS
  'Availability of externally reported metrics for this snapshot: NOT_REQUESTED, AVAILABLE, PARTIAL, or UNAVAILABLE. Missing metrics are never coerced to zero.';
COMMENT ON COLUMN performance_observations.insights_unavailable_reason IS
  'Sanitized, non-sensitive reason explaining why insight metrics were unavailable or partial.';
COMMENT ON COLUMN performance_observations.collection_run_id IS
  'Correlates all observations produced by a single read-only collection run.';

ALTER TABLE video_publications
  ADD COLUMN identity_match_method TEXT,
  ADD COLUMN identity_matched_at TIMESTAMPTZ;

ALTER TABLE video_publications
  ADD CONSTRAINT video_publication_identity_match_method_check
    CHECK (identity_match_method IS NULL
           OR identity_match_method IN ('PLATFORM_CONTENT_ID','PERMALINK','MANUAL'));

CREATE UNIQUE INDEX uq_video_publications_platform_url
  ON video_publications(platform, platform_url)
  WHERE platform_url IS NOT NULL;

COMMENT ON COLUMN video_publications.identity_match_method IS
  'How this publication was deterministically linked to external content: PLATFORM_CONTENT_ID, PERMALINK, or MANUAL.';
COMMENT ON COLUMN video_publications.identity_matched_at IS
  'Timestamp when deterministic identity matching last confirmed this linkage.';
