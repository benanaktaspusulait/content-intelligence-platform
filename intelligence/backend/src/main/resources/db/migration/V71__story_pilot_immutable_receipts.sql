-- Extend the existing ledger only. Historical non-pilot rows retain their
-- original contract; no historical records or canonical outcomes are updated.
CREATE FUNCTION prevent_story_pilot_evidence_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.payload->>'experimentVersion' = 'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1' THEN
    RAISE EXCEPTION 'Immutable story pilot evidence';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER story_pilot_evidence_immutable BEFORE UPDATE OR DELETE ON story_evolution_events
FOR EACH ROW EXECUTE FUNCTION prevent_story_pilot_evidence_mutation();

CREATE UNIQUE INDEX story_pilot_request_state_once
ON story_evolution_events (run_id, (payload->>'requestId'), (payload->>'state'))
WHERE payload->>'experimentVersion' = 'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1'
  AND payload->>'state' IN ('REQUEST_RESERVED','PROVIDER_RECEIPT')
  AND payload->>'requestId' IS NOT NULL;

CREATE FUNCTION prevent_story_pilot_grant_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.scope->>'experimentVersion' = 'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1'
    AND (OLD.authorization_payload IS DISTINCT FROM NEW.authorization_payload
      OR OLD.scope IS DISTINCT FROM NEW.scope OR OLD.owner_principal IS DISTINCT FROM NEW.owner_principal
      OR OLD.source_story_record_id IS DISTINCT FROM NEW.source_story_record_id
      OR OLD.source_story_sha256 IS DISTINCT FROM NEW.source_story_sha256
      OR OLD.deadline IS DISTINCT FROM NEW.deadline OR OLD.idempotency_key IS DISTINCT FROM NEW.idempotency_key) THEN
    RAISE EXCEPTION 'Immutable story pilot authorization';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER story_pilot_grant_immutable BEFORE UPDATE ON story_evolution_runs
FOR EACH ROW EXECUTE FUNCTION prevent_story_pilot_grant_mutation();
