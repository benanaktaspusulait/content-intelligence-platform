-- Different requested analysis versions must not reuse each other's active job.
DROP INDEX idx_analysis_jobs_one_active_per_video;
CREATE UNIQUE INDEX idx_analysis_jobs_one_active_identity
ON analysis_jobs(video_id, (COALESCE(request_payload->>'analysisVersion','sampled-visual-motion-v5')))
WHERE state IN ('QUEUED','RUNNING');
