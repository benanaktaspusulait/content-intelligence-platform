-- Extend public-comment delivery states without modifying the applied V21 migration.
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname
      INTO constraint_name
      FROM pg_constraint
     WHERE conrelid = 'meta_comment_replies'::regclass
       AND contype = 'c'
       AND pg_get_constraintdef(oid) LIKE '%RETRYABLE%';

    IF constraint_name IS NULL THEN
        RAISE EXCEPTION 'Meta comment reply status constraint not found';
    END IF;

    EXECUTE format('ALTER TABLE meta_comment_replies DROP CONSTRAINT %I', constraint_name);
END $$;

ALTER TABLE meta_comment_replies
    ADD CONSTRAINT ck_meta_comment_replies_status
    CHECK (status IN (
        'DRAFT',
        'PENDING_APPROVAL',
        'APPROVED',
        'REJECTED',
        'SENT',
        'FAILED',
        'RETRYABLE',
        'RECONCILIATION_REQUIRED'
    ));

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname
      INTO constraint_name
      FROM pg_constraint
     WHERE conrelid = 'meta_comment_delivery_attempts'::regclass
       AND contype = 'c'
       AND pg_get_constraintdef(oid) LIKE '%RETRYABLE%';

    IF constraint_name IS NULL THEN
        RAISE EXCEPTION 'Meta comment delivery attempt status constraint not found';
    END IF;

    EXECUTE format(
        'ALTER TABLE meta_comment_delivery_attempts DROP CONSTRAINT %I',
        constraint_name
    );
END $$;

ALTER TABLE meta_comment_delivery_attempts
    ADD CONSTRAINT ck_meta_comment_delivery_attempts_status
    CHECK (status IN (
        'SUBMITTING',
        'SENT',
        'FAILED',
        'RETRYABLE',
        'RECONCILIATION_REQUIRED'
    ));
