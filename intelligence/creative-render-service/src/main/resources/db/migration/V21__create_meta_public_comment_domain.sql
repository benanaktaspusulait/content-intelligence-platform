-- Canonical public Facebook Page / Instagram post-Reel comment domain.
-- Private conversations, DMs, and Messenger are intentionally not represented here.
CREATE TABLE meta_comment_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('FACEBOOK', 'INSTAGRAM')),
    external_account_id VARCHAR(200) NOT NULL,
    external_object_id VARCHAR(200) NOT NULL,
    external_thread_key VARCHAR(420) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'ARCHIVED')),
    last_provider_event_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_meta_comment_thread_external UNIQUE (platform, external_thread_key)
);

CREATE TABLE meta_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES meta_comment_threads(id) ON DELETE CASCADE,
    external_comment_id VARCHAR(200) NOT NULL,
    external_parent_comment_id VARCHAR(200),
    external_author_id VARCHAR(200),
    author_display_name VARCHAR(240),
    text TEXT NOT NULL,
    direction VARCHAR(20) NOT NULL DEFAULT 'INBOUND' CHECK (direction IN ('INBOUND', 'OUTBOUND')),
    moderation_status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED'
        CHECK (moderation_status IN ('RECEIVED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'RESOLVED')),
    provider_permalink TEXT,
    provider_created_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_meta_comment_external UNIQUE (thread_id, external_comment_id)
);

CREATE TABLE meta_comment_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES meta_comments(id) ON DELETE CASCADE,
    draft_text TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'
        CHECK (status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SENT', 'FAILED', 'RETRYABLE', 'RECONCILIATION_REQUIRED')),
    idempotency_key VARCHAR(240) NOT NULL UNIQUE,
    approved_by VARCHAR(200),
    approved_at TIMESTAMPTZ,
    provider_reply_id VARCHAR(200),
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE meta_comment_delivery_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reply_id UUID NOT NULL REFERENCES meta_comment_replies(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('SUBMITTING', 'SENT', 'FAILED', 'RETRYABLE', 'RECONCILIATION_REQUIRED')),
    provider_request_id VARCHAR(200),
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_meta_comment_delivery_attempt UNIQUE (reply_id, attempt_number)
);

CREATE INDEX idx_meta_comment_thread_object ON meta_comment_threads(platform, external_object_id);
CREATE INDEX idx_meta_comments_thread_created ON meta_comments(thread_id, provider_created_at);
CREATE INDEX idx_meta_comment_replies_status ON meta_comment_replies(status);
