CREATE TABLE caption_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id) ON DELETE CASCADE,
    platform VARCHAR(30) NOT NULL,
    caption TEXT NOT NULL,
    hashtags TEXT,
    source VARCHAR(30) NOT NULL DEFAULT 'GENERATED',
    created_by VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_caption_versions_asset_platform
    ON caption_versions(render_asset_id, platform, created_at DESC);

COMMENT ON TABLE caption_versions IS
    'Immutable social caption versions associated with a reviewed render asset.';
