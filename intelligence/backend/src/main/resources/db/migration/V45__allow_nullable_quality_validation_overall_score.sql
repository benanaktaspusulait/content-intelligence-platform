-- Family 9 permits quality reports whose score is not evaluable yet.
ALTER TABLE quality_validations
  ALTER COLUMN overall_score DROP NOT NULL;
