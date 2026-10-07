-- Durable, owner-scoped Meta OAuth connection state.
CREATE TABLE meta_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_key VARCHAR(200) NOT NULL,
  provider VARCHAR(30) NOT NULL DEFAULT 'META',
  provider_user_id VARCHAR(200),
  facebook_page_id VARCHAR(100) NOT NULL,
  instagram_account_id VARCHAR(100),
  instagram_account_type VARCHAR(80),
  user_access_token_encrypted TEXT,
  page_access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  granted_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  status VARCHAR(30) NOT NULL CHECK (status IN ('CONNECTED', 'DEGRADED', 'EXPIRED', 'REVOKED', 'NOT_CONFIGURED')),
  capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
  facebook_page_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  instagram_account_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  issued_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ,
  last_validated_at TIMESTAMPTZ,
  failure_reason TEXT,
  provider_error_code VARCHAR(100),
  entity_version BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_meta_connection_owner_provider_identity
    UNIQUE (owner_key, provider, provider_user_id, facebook_page_id, instagram_account_id),
  CONSTRAINT uq_meta_connection_owner_provider_page
    UNIQUE (owner_key, provider, facebook_page_id)
);

CREATE INDEX idx_meta_connections_owner_status
  ON meta_connections(owner_key, status);
CREATE INDEX idx_meta_connections_owner_expiry
  ON meta_connections(owner_key, expires_at);
CREATE INDEX idx_meta_connections_provider_identity
  ON meta_connections(provider, provider_user_id, facebook_page_id, instagram_account_id);

COMMENT ON TABLE meta_connections IS
  'Durable owner-scoped Meta OAuth state; token columns contain encrypted provider material only.';
COMMENT ON COLUMN meta_connections.user_access_token_encrypted IS
  'AES-GCM encrypted Meta user-context token; never serialized as an API field.';
COMMENT ON COLUMN meta_connections.page_access_token_encrypted IS
  'AES-GCM encrypted Meta Page token; never serialized as an API field.';
COMMENT ON COLUMN meta_connections.capabilities IS
  'Fail-closed capability admission statuses keyed by MetaCapability name.';
