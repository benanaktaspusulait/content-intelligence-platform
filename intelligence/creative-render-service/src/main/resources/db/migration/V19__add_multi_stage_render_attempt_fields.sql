-- Durable operation identity for automatic FIRST_FRAME -> VIDEO plans.
ALTER TABLE render_attempts
    ADD COLUMN provider_operation VARCHAR(20),
    ADD COLUMN first_frame_asset_id UUID REFERENCES render_assets(id);

CREATE INDEX idx_render_attempts_first_frame_asset_id
    ON render_attempts(first_frame_asset_id);
