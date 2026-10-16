-- Run-local drafts do not create production PromptVersions or CPQ grades.
CREATE TABLE optimization_runs (
 id UUID PRIMARY KEY, owner_principal TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 scope JSONB NOT NULL, scope_sha256 CHAR(64) NOT NULL, grant_payload JSONB NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('READY','RUNNING','STOPPED','COMPLETED','PAUSED')),
 progress JSONB NOT NULL, cancel_requested BOOLEAN NOT NULL DEFAULT false,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deadline TIMESTAMPTZ NOT NULL,
 lease_started TIMESTAMPTZ, UNIQUE(owner_principal,idempotency_key)
);
CREATE TABLE optimization_run_requests (
 id UUID PRIMARY KEY, run_id UUID NOT NULL REFERENCES optimization_runs(id), round_number INT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('GENERATION','SOURCE_FIDELITY','CRITIC')),
 input JSONB NOT NULL, input_sha256 CHAR(64) NOT NULL, authorization_payload JSONB NOT NULL,
 reserved_usd NUMERIC(16,10) NOT NULL CHECK(reserved_usd>0),
 state TEXT NOT NULL CHECK(state IN ('AUTHORIZED','DISPATCHING','COMPLETED','FAILED_OR_AMBIGUOUS')),
 response JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ,
 UNIQUE(run_id,round_number,role)
);
CREATE TABLE optimization_run_drafts (
 id UUID PRIMARY KEY, run_id UUID NOT NULL REFERENCES optimization_runs(id), parent_id UUID,
 round_number INT NOT NULL, prompt_sha256 CHAR(64) NOT NULL, payload JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(run_id,round_number)
);
CREATE TABLE optimization_run_events (
 id UUID PRIMARY KEY, run_id UUID NOT NULL REFERENCES optimization_runs(id), payload JSONB NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER optimization_drafts_immutable BEFORE UPDATE OR DELETE ON optimization_run_drafts FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE TRIGGER optimization_events_immutable BEFORE UPDATE OR DELETE ON optimization_run_events FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE FUNCTION protect_optimization_bindings() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='optimization_runs' THEN
  IF (NEW.id,NEW.owner_principal,NEW.idempotency_key,NEW.scope,NEW.scope_sha256,NEW.grant_payload,NEW.created_at,NEW.deadline) IS DISTINCT FROM (OLD.id,OLD.owner_principal,OLD.idempotency_key,OLD.scope,OLD.scope_sha256,OLD.grant_payload,OLD.created_at,OLD.deadline) THEN RAISE EXCEPTION 'Immutable optimization authorization'; END IF;
 ELSE
  IF (NEW.id,NEW.run_id,NEW.round_number,NEW.role,NEW.input,NEW.input_sha256,NEW.authorization_payload,NEW.reserved_usd,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.run_id,OLD.round_number,OLD.role,OLD.input,OLD.input_sha256,OLD.authorization_payload,OLD.reserved_usd,OLD.created_at) THEN RAISE EXCEPTION 'Immutable optimization request scope'; END IF;
  IF OLD.state IN ('COMPLETED','FAILED_OR_AMBIGUOUS') THEN RAISE EXCEPTION 'Immutable terminal provider evidence'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER optimization_run_bindings BEFORE UPDATE ON optimization_runs FOR EACH ROW EXECUTE FUNCTION protect_optimization_bindings();
CREATE TRIGGER optimization_request_bindings BEFORE UPDATE ON optimization_run_requests FOR EACH ROW EXECUTE FUNCTION protect_optimization_bindings();
