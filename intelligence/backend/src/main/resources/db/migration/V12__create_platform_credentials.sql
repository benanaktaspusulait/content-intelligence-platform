-- Platform OAuth credentials table
CREATE TABLE platform_credentials (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL UNIQUE,
    platform_user_id VARCHAR(100),
    platform_username VARCHAR(100),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_type VARCHAR(50),
    scope TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_refreshed_at TIMESTAMP,
    connected_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_platform_credentials_platform ON platform_credentials(platform);
CREATE INDEX idx_platform_credentials_active ON platform_credentials(is_active);
CREATE INDEX idx_platform_credentials_expires ON platform_credentials(expires_at);

COMMENT ON TABLE platform_credentials IS 'OAuth credentials for connected social media platforms (encrypted)';
COMMENT ON COLUMN platform_credentials.platform IS 'Platform name: TIKTOK, YOUTUBE, FACEBOOK, INSTAGRAM';
COMMENT ON COLUMN platform_credentials.access_token_encrypted IS 'AES-256 encrypted access token';
COMMENT ON COLUMN platform_credentials.refresh_token_encrypted IS 'AES-256 encrypted refresh token';
COMMENT ON COLUMN platform_credentials.is_active IS 'Whether credential is currently valid and in use';
