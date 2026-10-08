ALTER TABLE prompt_versions ADD COLUMN parent_prompt_version_id BIGINT REFERENCES prompt_versions(id);
CREATE INDEX prompt_versions_parent ON prompt_versions(parent_prompt_version_id);
