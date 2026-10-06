-- Provider identity, multi-stage lineage, and original/final media metadata.
ALTER TABLE render_assets
    ADD COLUMN provider_job_id VARCHAR(100),
    ADD COLUMN provider_asset_id VARCHAR(200),
    ADD COLUMN asset_source VARCHAR(30),
    ADD COLUMN parent_asset_id UUID REFERENCES render_assets(id),
    ADD COLUMN character_refs JSONB,
    ADD COLUMN prompt_hash VARCHAR(64),
    ADD COLUMN contract_hash VARCHAR(64),
    ADD COLUMN original_width INTEGER,
    ADD COLUMN original_height INTEGER,
    ADD COLUMN final_width INTEGER,
    ADD COLUMN final_height INTEGER,
    ADD COLUMN processing_status VARCHAR(30) NOT NULL DEFAULT 'REGISTERED',
    ADD COLUMN processing_error TEXT,
    ADD COLUMN processing_attempt_count INTEGER NOT NULL DEFAULT 1;

UPDATE render_assets
SET final_width = width,
    final_height = height,
    original_width = width,
    original_height = height,
    asset_source = CASE WHEN is_mock THEN 'MOCK' ELSE 'OPENART' END
WHERE final_width IS NULL;

CREATE INDEX idx_render_assets_provider_job_id ON render_assets(provider_job_id);
CREATE INDEX idx_render_assets_parent_asset_id ON render_assets(parent_asset_id);
