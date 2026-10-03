-- Complete the quality-validation status and independent-revalidation model.

ALTER TABLE quality_validations
  DROP CONSTRAINT IF EXISTS quality_validations_status_check;

ALTER TABLE quality_validations
  ADD CONSTRAINT quality_validations_status_check
    CHECK (status IN ('RENDER_READY', 'NEEDS_REVISION', 'BLOCKED', 'SERVICE_ERROR'));

ALTER TABLE quality_validations
  ADD COLUMN validation_run_id UUID;

ALTER TABLE quality_validations
  ADD CONSTRAINT quality_validations_validation_run_id_unique UNIQUE (validation_run_id),
  ADD CONSTRAINT quality_validations_independent_run_check
    CHECK (
      independent_revalidation_id IS NULL
      OR validation_run_id IS NULL
      OR independent_revalidation_id <> validation_run_id
    );

COMMENT ON COLUMN quality_validations.validation_run_id IS
  'Stable identity of this validation execution. A primary validation references a different row through independent_revalidation_id.';
