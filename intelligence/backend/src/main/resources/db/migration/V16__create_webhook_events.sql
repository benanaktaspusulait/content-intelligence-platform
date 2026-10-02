-- Webhook events table
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    platform_post_id VARCHAR(100),
    publication_job_id UUID,
    payload TEXT NOT NULL,
    signature TEXT,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_events_platform ON webhook_events(platform);
CREATE INDEX idx_webhook_events_is_processed ON webhook_events(is_processed);
CREATE INDEX idx_webhook_events_job_id ON webhook_events(publication_job_id);
CREATE INDEX idx_webhook_events_post_id ON webhook_events(platform_post_id);
CREATE INDEX idx_webhook_events_created_at ON webhook_events(created_at);

COMMENT ON TABLE webhook_events IS 'Incoming webhook events from social media platforms';
COMMENT ON COLUMN webhook_events.event_type IS 'Type of event (e.g., video.processing_complete, published)';
COMMENT ON COLUMN webhook_events.signature IS 'Webhook signature for verification (HMAC-SHA256)';
COMMENT ON COLUMN webhook_events.retry_count IS 'Number of processing retry attempts';
