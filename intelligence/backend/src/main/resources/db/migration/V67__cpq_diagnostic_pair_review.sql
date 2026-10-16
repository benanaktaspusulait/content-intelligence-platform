-- Reuse the immutable machine-review ledger with a separately admitted diagnostic purpose.
ALTER TABLE cpq_owner_pilots DROP CONSTRAINT cpq_owner_pilots_policy_version_check;
ALTER TABLE cpq_owner_pilots ADD CONSTRAINT cpq_owner_pilots_policy_version_check
 CHECK(policy_version IN ('OWNER_MACHINE_PILOT_V1','DRAFT_COMPARATIVE_REVIEW_V1'));
