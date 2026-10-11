-- Visual preparation may precede a RenderJob. Existing job-bound plans retain one-to-one
-- uniqueness; preparation records without a job are identified by content/prompt lineage.
ALTER TABLE visual_reference_plans ALTER COLUMN render_job_id DROP NOT NULL;
ALTER TABLE visual_reference_plans DROP CONSTRAINT IF EXISTS visual_reference_plans_render_job_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_visual_reference_plans_render_job
    ON visual_reference_plans(render_job_id) WHERE render_job_id IS NOT NULL;
