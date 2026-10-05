-- Immutable production-intent and prompt-constraint snapshot for new render jobs.
-- Legacy rows remain readable and are explicitly marked unavailable by the application.
ALTER TABLE render_jobs
  ADD COLUMN creative_contract_version VARCHAR(80),
  ADD COLUMN creative_contract_status VARCHAR(40),
  ADD COLUMN creative_contract_snapshot JSONB,
  ADD COLUMN compiled_generation_constraints JSONB,
  ADD COLUMN constraint_compiler_version VARCHAR(80),
  ADD COLUMN compiled_constraints_sha256 VARCHAR(64),
  ADD COLUMN generation_prompt_snapshot TEXT;

COMMENT ON COLUMN render_jobs.creative_contract_snapshot IS
  'Immutable normalized creative intent derived from the canonical parsed prompt at queue time.';
COMMENT ON COLUMN render_jobs.compiled_generation_constraints IS
  'Immutable provider-facing constraints compiled from the creative production contract.';
COMMENT ON COLUMN render_jobs.generation_prompt_snapshot IS
  'Exact prompt payload sent to the generation provider, including the compiled constraints.';
