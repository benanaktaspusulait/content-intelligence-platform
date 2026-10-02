CREATE INDEX idx_intervention_events_video_platform_time
  ON intervention_events(video_id, platform, event_time);

CREATE OR REPLACE FUNCTION prevent_intervention_event_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'intervention events are append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER intervention_events_append_only
BEFORE UPDATE OR DELETE ON intervention_events
FOR EACH ROW EXECUTE FUNCTION prevent_intervention_event_mutation();
