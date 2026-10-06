-- A worker may poll the same completed OpenArt history more than once after a crash.
-- One provider history can therefore contribute to the ledger only once.
-- Preserve any pre-existing duplicate rows while making their operation identities unique so an
-- upgrade cannot fail merely because an older deployment recorded the same history twice.
WITH ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY openart_job_id, operation
               ORDER BY logged_at, id
           ) AS row_number
    FROM openart_credit_log
    WHERE openart_job_id IS NOT NULL
)
UPDATE openart_credit_log AS log
SET operation = LEFT(log.operation, 13) || '_DUP_' || LEFT(log.id::text, 8)
FROM ranked
WHERE log.id = ranked.id
  AND ranked.row_number > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_openart_credit_log_provider_operation
    ON openart_credit_log (openart_job_id, operation)
    WHERE openart_job_id IS NOT NULL;
