-- A worker may poll the same completed OpenArt history more than once after a crash.
-- One provider history can therefore contribute to the ledger only once.
CREATE UNIQUE INDEX IF NOT EXISTS uq_openart_credit_log_provider_operation
    ON openart_credit_log (openart_job_id, operation)
    WHERE openart_job_id IS NOT NULL;
