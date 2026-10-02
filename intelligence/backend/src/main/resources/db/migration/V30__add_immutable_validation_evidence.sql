-- Immutable validation evidence (Slice B Task 1).
--
-- Adds the fields creative-render-service's render queue gate consults through the internal
-- evidence endpoint. All columns are nullable: existing quality_validations rows predate this
-- model and must never be treated as complete evidence (ValidationEvidenceService fails closed
-- on any gap, regardless of this migration). Non-destructive: no existing column, row, or
-- constraint from V1-V29 is altered.
--
-- NOTE: originally planned as V29 in the readiness plan; renumbered to V30 because the Meta
-- read-only integration took V29 (see V29__add_meta_readonly_snapshot_fields.sql).

ALTER TABLE quality_validations
  ADD COLUMN content_id BIGINT,
  ADD COLUMN prompt_version_id BIGINT,
  ADD COLUMN prompt_sha256 TEXT,
  ADD COLUMN deterministic_ruleset_version TEXT,
  ADD COLUMN semantic_provider TEXT,
  ADD COLUMN semantic_model_version TEXT,
  ADD COLUMN producibility_validator_version TEXT,
  ADD COLUMN independent_revalidation_id UUID,
  ADD COLUMN independently_revalidated_at TIMESTAMPTZ,
  ADD COLUMN validated_at TIMESTAMPTZ,
  ADD COLUMN expires_at TIMESTAMPTZ;

ALTER TABLE quality_validations
  ADD CONSTRAINT quality_validations_blocker_count_nonnegative_check
    CHECK (blocker_count >= 0),
  ADD CONSTRAINT quality_validations_critical_count_nonnegative_check
    CHECK (critical_count >= 0),
  ADD CONSTRAINT quality_validations_warning_count_nonnegative_check
    CHECK (warning_count >= 0),
  ADD CONSTRAINT quality_validations_prompt_sha256_format_check
    CHECK (prompt_sha256 IS NULL OR prompt_sha256 ~ '^[0-9a-f]{64}$');

CREATE INDEX idx_quality_validations_content_prompt_timeline
  ON quality_validations(content_id, prompt_version_id, created_at DESC)
  WHERE content_id IS NOT NULL AND prompt_version_id IS NOT NULL;

-- At most one validation record may claim a given independent revalidation: a fixer cannot
-- approve its own output, and a single independent revalidation cannot authorize two different
-- validation records.
CREATE UNIQUE INDEX uq_quality_validations_independent_revalidation_id
  ON quality_validations(independent_revalidation_id)
  WHERE independent_revalidation_id IS NOT NULL;

COMMENT ON COLUMN quality_validations.content_id IS
  'External content ID this validation is linked to. NULL for standalone/unlinked validations, which remain visible but are permanently non-renderable.';
COMMENT ON COLUMN quality_validations.prompt_version_id IS
  'External immutable prompt version ID this validation is linked to.';
COMMENT ON COLUMN quality_validations.prompt_sha256 IS
  'SHA-256 (lowercase hex) of the immutable UTF-8 prompt text that was actually validated.';
COMMENT ON COLUMN quality_validations.deterministic_ruleset_version IS
  'Version of the deterministic ruleset applied, independent of the legacy ruleset_version column.';
COMMENT ON COLUMN quality_validations.semantic_provider IS
  'Semantic LLM QA provider identity (populated once the semantic QA stage exists).';
COMMENT ON COLUMN quality_validations.semantic_model_version IS
  'Semantic LLM QA model version identity.';
COMMENT ON COLUMN quality_validations.producibility_validator_version IS
  'AI producibility QA validator version identity.';
COMMENT ON COLUMN quality_validations.independent_revalidation_id IS
  'Identity of the separate, independent revalidation invocation that approved this record. A fixer can never approve its own output.';
COMMENT ON COLUMN quality_validations.independently_revalidated_at IS
  'Timestamp of the independent revalidation referenced by independent_revalidation_id.';
COMMENT ON COLUMN quality_validations.validated_at IS
  'Timestamp this validation evidence was produced.';
COMMENT ON COLUMN quality_validations.expires_at IS
  'Timestamp after which this evidence is stale and must not authorize render, per the configured freshness policy.';
