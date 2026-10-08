CREATE TABLE prompt_creative_provenance (
 prompt_version_id BIGINT PRIMARY KEY REFERENCES prompt_versions(id),
 creative_role_record_id UUID NOT NULL REFERENCES post_family_workflow_events(id),
 operator_edited BOOLEAN NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER prompt_creative_provenance_append_only BEFORE UPDATE OR DELETE ON prompt_creative_provenance
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
