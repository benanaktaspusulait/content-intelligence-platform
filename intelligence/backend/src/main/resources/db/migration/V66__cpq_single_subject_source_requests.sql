-- Preserve old batch rows (NULL subject) and immutable evidence; scope only new source requests.
ALTER TABLE cpq_machine_requests ADD COLUMN subject_prompt_sha256 CHAR(64);
ALTER TABLE cpq_machine_requests ADD CONSTRAINT cpq_source_subject_scope CHECK
 (subject_prompt_sha256 IS NULL OR (slot='SOURCE_FIDELITY' AND subject_prompt_sha256 ~ '^[0-9a-f]{64}$'));
ALTER TABLE cpq_machine_requests DROP CONSTRAINT cpq_machine_requests_pilot_id_slot_key;
CREATE UNIQUE INDEX cpq_legacy_and_critic_slot ON cpq_machine_requests(pilot_id,slot)
 WHERE subject_prompt_sha256 IS NULL;
CREATE UNIQUE INDEX cpq_source_subject_slot ON cpq_machine_requests(pilot_id,slot,subject_prompt_sha256)
 WHERE subject_prompt_sha256 IS NOT NULL;
