-- V3: Immutable validation evidence snapshot + idempotency keys on render_jobs (Slice B Task 2).
--
-- The render queue gate (ValidationEvidencePolicy) accepts a render request only when the
-- intelligence backend's validation evidence satisfies every hard precondition in the design doc
-- (status RENDER_READY, zero blocker/critical counts, independent revalidation present, matching
-- content/prompt identity, every required version identity present, not expired). The accepted
-- evidence is then copied into the render job row at queue time, so a render job always carries
-- an immutable record of exactly what authorized it - never a live reference back to intelligence.
--
-- All new columns are nullable, matching the pattern already used for the intelligence backend's
-- own evidence table (V30__add_immutable_validation_evidence.sql there): V2's legacy copy already
-- populates render_jobs from the pre-evidence public.render_jobs schema, and those legacy rows
-- (and any row inserted outside RenderJobQueueService) have no evidence to carry by construction.
-- Completeness is enforced in application code (RenderJobQueueService always sets every evidence
-- field before insert) rather than with a blanket NOT NULL, which would have rejected the exact
-- legacy rows V2 is responsible for carrying forward.

ALTER TABLE render_jobs
  ADD COLUMN validation_record_id BIGINT,
  ADD COLUMN evidence_deterministic_ruleset_version TEXT,
  ADD COLUMN evidence_semantic_provider TEXT,
  ADD COLUMN evidence_semantic_model_version TEXT,
  ADD COLUMN evidence_producibility_validator_version TEXT,
  ADD COLUMN evidence_independent_revalidation_id UUID,
  ADD COLUMN evidence_independently_revalidated_at TIMESTAMPTZ,
  ADD COLUMN evidence_validated_at TIMESTAMPTZ,
  ADD COLUMN idempotency_key TEXT,
  ADD COLUMN request_fingerprint VARCHAR(64);

-- idempotency_key/request_fingerprint are likewise nullable for the same reason (legacy rows have
-- no Idempotency-Key to carry), but when idempotency_key IS set it must be unique and the
-- fingerprint must be well-formed - both enforced unconditionally since neither constraint can
-- ever be violated by a NULL value.
ALTER TABLE render_jobs
  ADD CONSTRAINT render_jobs_idempotency_key_unique UNIQUE (idempotency_key),
  ADD CONSTRAINT render_jobs_request_fingerprint_format_check
    CHECK (request_fingerprint IS NULL OR request_fingerprint ~ '^[0-9a-f]{64}$');

CREATE INDEX idx_render_jobs_validation_record_id ON render_jobs(validation_record_id);

COMMENT ON COLUMN render_jobs.validation_record_id IS
  'The intelligence backend validation record ID whose evidence authorized this render job. NULL for legacy rows copied by V2, which predate this evidence model.';
COMMENT ON COLUMN render_jobs.idempotency_key IS
  'Client-supplied Idempotency-Key header value. Unique when present: a second request with the same key is a replay (same fingerprint) or a conflict (different fingerprint), never a second row. NULL for legacy rows.';
COMMENT ON COLUMN render_jobs.request_fingerprint IS
  'SHA-256 (lowercase hex) of the canonical JSON (sorted object keys) of the queue request body, used to distinguish a legitimate idempotent replay from a conflicting reuse of the same key.';

