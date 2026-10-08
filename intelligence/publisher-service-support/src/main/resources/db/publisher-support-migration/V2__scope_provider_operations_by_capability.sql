ALTER TABLE publisher_support.provider_operation_records
  ADD COLUMN publisher_capability VARCHAR(64) NOT NULL DEFAULT 'legacy';

UPDATE publisher_support.provider_operation_records
SET publisher_capability = 'facebook_reels'
WHERE command_idempotency_key LIKE 'facebook_reels:%';

UPDATE publisher_support.provider_operation_records
SET publisher_capability = 'instagram_reels'
WHERE command_idempotency_key LIKE 'instagram_reels:%';

ALTER TABLE publisher_support.provider_operation_records
  DROP CONSTRAINT uq_provider_operation_command_idempotency_key;

ALTER TABLE publisher_support.provider_operation_records
  ADD CONSTRAINT uq_provider_operation_capability_key
  UNIQUE (publisher_capability, command_idempotency_key);

CREATE INDEX idx_provider_operation_capability_attempt
  ON publisher_support.provider_operation_records(publisher_capability, publication_attempt_id);
