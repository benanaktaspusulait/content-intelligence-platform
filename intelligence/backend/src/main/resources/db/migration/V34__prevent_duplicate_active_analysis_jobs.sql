-- V34: prevent two active (QUEUED or RUNNING) analysis jobs existing for the same video at once.
-- Enforced at the database level (not just application-level check-then-insert) so concurrent
-- enqueue requests cannot both succeed in creating a duplicate active job.
CREATE UNIQUE INDEX idx_analysis_jobs_one_active_per_video
  ON analysis_jobs (video_id)
  WHERE state IN ('QUEUED', 'RUNNING');
