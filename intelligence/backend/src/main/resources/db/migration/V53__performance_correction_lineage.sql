CREATE TABLE performance_observation_corrections (
  observation_id UUID PRIMARY KEY REFERENCES performance_observations(id),
  correction_of_id UUID NOT NULL UNIQUE REFERENCES performance_observations(id),
  reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (observation_id <> correction_of_id)
);
CREATE TRIGGER performance_corrections_append_only BEFORE UPDATE OR DELETE ON performance_observation_corrections
FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
CREATE VIEW effective_performance_observations AS
SELECT p.* FROM performance_observations p
WHERE NOT EXISTS (SELECT 1 FROM performance_observation_corrections c WHERE c.correction_of_id=p.id);
