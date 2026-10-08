CREATE TABLE content_source_path_aliases (
  source_path TEXT PRIMARY KEY,
  content_id BIGINT NOT NULL REFERENCES contents(id),
  source_sha256 TEXT NOT NULL,
  reason TEXT NOT NULL CHECK(length(trim(reason))>0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER content_source_aliases_append_only BEFORE UPDATE OR DELETE ON content_source_path_aliases
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
