-- V7: Contents and Prompt Versions tables

CREATE TYPE content_type AS ENUM ('EPISODE', 'SHORT', 'REEL');
CREATE TYPE content_status AS ENUM ('DRAFT', 'VALIDATING', 'RENDER_READY', 'RENDERING', 'RENDERED', 'PUBLISHED');

CREATE TABLE contents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type content_type NOT NULL,
    status content_status NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contents_status ON contents(status);
CREATE INDEX idx_contents_type ON contents(type);
CREATE INDEX idx_contents_created_at ON contents(created_at);

CREATE TABLE prompt_versions (
    id BIGSERIAL PRIMARY KEY,
    content_id BIGINT NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    raw_text TEXT NOT NULL,
    parsed_ir JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_id, version_number)
);

CREATE INDEX idx_prompt_versions_content_id ON prompt_versions(content_id);
CREATE INDEX idx_prompt_versions_created_at ON prompt_versions(created_at);

COMMENT ON TABLE contents IS 'Content items (episodes, shorts, reels) to be validated and rendered';
COMMENT ON TABLE prompt_versions IS 'Version history of prompts for each content item, with parsed IR';
