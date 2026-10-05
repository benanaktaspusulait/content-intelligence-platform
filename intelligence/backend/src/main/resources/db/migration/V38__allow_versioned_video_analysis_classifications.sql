-- v1 creative-quality labels remain valid for historical rows; v2 uses motion-evidence labels.
ALTER TABLE creative_analyses
  DROP CONSTRAINT IF EXISTS creative_analyses_classification_check;

ALTER TABLE creative_analyses
  ADD CONSTRAINT creative_analyses_classification_check
  CHECK (classification IN (
    'BAD', 'AVERAGE_FIXABLE', 'GOOD', 'WINNER_CANDIDATE',
    'HIGH_MOTION_EVIDENCE', 'MODERATE_MOTION_EVIDENCE', 'LOW_MOTION_EVIDENCE'
  ));
