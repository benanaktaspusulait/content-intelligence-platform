-- Part 04: make unavailable QA explicit and replace client supplied publication paths with
-- canonical render-asset identity. Existing rows remain readable but cannot satisfy the new
-- publication gate until they have canonical asset/account identity.

ALTER TABLE render_qa_results
  ALTER COLUMN physics_consistent DROP NOT NULL,
  ALTER COLUMN has_object_duplication DROP NOT NULL;

ALTER TABLE render_assets
  ADD COLUMN asset_version INTEGER,
  ADD COLUMN sha256 VARCHAR(64),
  ADD COLUMN media_verified BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN is_mock BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN quarantined BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN video_id UUID,
  ADD COLUMN variant_id UUID;

UPDATE render_assets
SET asset_version = COALESCE(
  NULLIF(substring(relative_path FROM 'v([0-9]+)'), '')::INTEGER,
  1
)
WHERE asset_version IS NULL;

ALTER TABLE render_assets ALTER COLUMN asset_version SET NOT NULL;

CREATE UNIQUE INDEX uq_render_asset_version
  ON render_assets(content_id, asset_type, asset_version);
CREATE UNIQUE INDEX uq_render_asset_current
  ON render_assets(content_id, asset_type)
  WHERE is_current;
CREATE INDEX idx_render_assets_variant_id ON render_assets(variant_id);

ALTER TABLE publication_jobs
  ADD COLUMN render_asset_id UUID REFERENCES render_assets(id),
  ADD COLUMN video_id UUID,
  ADD COLUMN variant_id UUID,
  ADD COLUMN platform_account_id VARCHAR(200),
  ADD COLUMN idempotency_key VARCHAR(200);

CREATE UNIQUE INDEX uq_publication_idempotency_key
  ON publication_jobs(idempotency_key)
  WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_publication_render_asset_id ON publication_jobs(render_asset_id);
CREATE INDEX idx_publication_variant_id ON publication_jobs(variant_id);
CREATE INDEX idx_publication_remote_identity
  ON publication_jobs(platform, platform_account_id, platform_post_id);

ALTER TABLE scheduled_publications
  ADD COLUMN render_asset_id UUID REFERENCES render_assets(id),
  ADD COLUMN platform_account_id VARCHAR(200);

CREATE INDEX idx_scheduled_render_asset_id ON scheduled_publications(render_asset_id);

COMMENT ON COLUMN publication_jobs.video_path IS
  'Server-resolved path snapshot retained for execution/legacy reads; never accepted from the publication API.';
