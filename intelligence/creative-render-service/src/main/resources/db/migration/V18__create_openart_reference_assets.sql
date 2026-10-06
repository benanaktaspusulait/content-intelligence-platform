-- Durable local/OpenArt reference catalog. No provider credential material is stored here.
CREATE TABLE openart_reference_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_key VARCHAR(160) NOT NULL,
    display_name VARCHAR(240) NOT NULL,
    source VARCHAR(30) NOT NULL CHECK (source IN ('LOCAL', 'OPENART_WORKSPACE')),
    media_type VARCHAR(30) NOT NULL,
    provider_asset_id VARCHAR(200),
    provider_url TEXT,
    local_path TEXT,
    sha256 VARCHAR(64),
    status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE'
        CHECK (status IN ('AVAILABLE', 'MISSING', 'UNSUPPORTED', 'ERROR')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_openart_reference_source_key UNIQUE (source, canonical_key)
);

CREATE UNIQUE INDEX uq_openart_reference_provider_id
    ON openart_reference_assets (provider_asset_id)
    WHERE provider_asset_id IS NOT NULL;
CREATE INDEX idx_openart_reference_canonical_key
    ON openart_reference_assets (canonical_key);
