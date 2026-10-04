CREATE TABLE oauth_states (
    state_hash VARCHAR(64) PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_oauth_states_expiry ON oauth_states(expires_at);
