-- Folder proximity is a candidate, never generation proof. Preserve each operator resolution.
CREATE TABLE video_prompt_links (
 id BIGSERIAL PRIMARY KEY,
 video_id UUID NOT NULL REFERENCES videos(id),
 prompt_version_id BIGINT NOT NULL REFERENCES prompt_versions(id),
 origin VARCHAR(24) NOT NULL CHECK (origin IN ('ORIGINAL','RECONSTRUCTED')),
 reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
 video_hash TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX video_prompt_links_latest ON video_prompt_links(video_id, id DESC);
