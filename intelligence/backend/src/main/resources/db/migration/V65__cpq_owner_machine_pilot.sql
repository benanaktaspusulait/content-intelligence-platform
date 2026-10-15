-- Ungraded pilot evidence never participates in human calibration tables or activation.
CREATE TABLE cpq_owner_pilots (
 pilot_id UUID PRIMARY KEY, owner_principal TEXT NOT NULL, policy_version TEXT NOT NULL CHECK(policy_version='OWNER_MACHINE_PILOT_V1'),
 scope_sha256 CHAR(64) NOT NULL, snapshot JSONB NOT NULL, total_budget_usd NUMERIC(12,6) NOT NULL CHECK(total_budget_usd>0 AND total_budget_usd<=20), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE cpq_machine_requests (
 request_id UUID PRIMARY KEY, pilot_id UUID NOT NULL REFERENCES cpq_owner_pilots(pilot_id), slot TEXT NOT NULL CHECK(slot IN ('SOURCE_FIDELITY','CRITIC_A','CRITIC_B')),
 idempotency_key TEXT NOT NULL, authorized_by TEXT NOT NULL, authorization_payload JSONB NOT NULL, input_sha256 CHAR(64) NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('AUTHORIZED','DISPATCHING','COMPLETED','FAILED_OR_AMBIGUOUS')), reserved_usd NUMERIC(12,6) NOT NULL CHECK(reserved_usd>0),
 input JSONB NOT NULL, response JSONB, failure TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ,
 UNIQUE(pilot_id,slot), UNIQUE(pilot_id,idempotency_key)
);
CREATE TABLE cpq_pilot_evidence (
 evidence_id UUID PRIMARY KEY, pilot_id UUID NOT NULL REFERENCES cpq_owner_pilots(pilot_id), request_id UUID UNIQUE REFERENCES cpq_machine_requests(request_id),
 evidence_type TEXT NOT NULL CHECK(evidence_type IN ('MACHINE_REVIEW','OWNER_DECISION')), actor TEXT NOT NULL, payload JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK((evidence_type='MACHINE_REVIEW' AND request_id IS NOT NULL) OR (evidence_type='OWNER_DECISION' AND request_id IS NULL))
);
CREATE TRIGGER cpq_owner_pilots_immutable BEFORE UPDATE OR DELETE ON cpq_owner_pilots FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
CREATE TRIGGER cpq_pilot_evidence_immutable BEFORE UPDATE OR DELETE ON cpq_pilot_evidence FOR EACH ROW EXECUTE FUNCTION prevent_cpq_evidence_mutation();
