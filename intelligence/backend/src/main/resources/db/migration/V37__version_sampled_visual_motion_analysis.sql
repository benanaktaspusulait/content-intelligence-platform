-- Versioned rendered-video analysis semantics. Historical rows remain LEGACY and immutable.
ALTER TABLE creative_analyses
  ADD COLUMN analysis_type TEXT NOT NULL DEFAULT 'LEGACY';

ALTER TABLE creative_analyses
  ALTER COLUMN analysis_type DROP DEFAULT;

COMMENT ON COLUMN creative_analyses.analysis_type IS
  'Semantic type of the analyzer that produced this row. LEGACY preserves v1 meaning; v2 uses SAMPLED_VISUAL_MOTION.';
