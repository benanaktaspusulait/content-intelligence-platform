-- TEST ONLY. Execute against the disposable database; never production.
-- This proves fixture identity, not creative admission or visual quality.
DO $$ BEGIN
  IF current_database() <> 'pompom_idea_acceptance_20261021' THEN
    RAISE EXCEPTION 'This fixture is restricted to the isolated acceptance database';
  END IF;
END $$;
INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload)
SELECT gen_random_uuid(), 'IDEA_EVALUATION', payload->>'candidateId',
 jsonb_build_object(
   'candidateId',payload->>'candidateId', 'revision',2,
   'status','EVALUATED', 'eligible',true, 'fixtureOnly',true,
   'policyVersion','ISOLATED_SELECTION_TEST_ONLY',
   'createdAt',clock_timestamp(),
   'gates',jsonb_build_array(jsonb_build_object(
     'gate','FIXTURE_IDENTITY_ASSERTION', 'mandatory',true, 'status','PASS',
     'evidence',payload->'payload'->>'title',
     'reason','ISOLATED TEST ONLY: exact fixture title verified by SQL predicate. Exercises selection persistence; does not assert creative eligibility.')))
FROM post_family_workflow_events
WHERE kind='IDEA_CANDIDATE'
 AND payload->>'draftId'='11111111-2222-4333-8444-555555555555'
 AND payload->'payload'->>'title'='Fixture: Heavy Reflection';
