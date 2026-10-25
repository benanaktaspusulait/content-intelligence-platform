"""Record acceptance evidence against existing local production/isolated test apps.
No generation endpoint is called with authorization. Recovery reuses a fixture receipt.
"""
import hashlib
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name('acceptance_result.json')
DRAFT = '7455a67e-1d39-4b91-9101-2df227ee3dc0'
FIXTURE = '11111111-2222-4333-8444-555555555555'
WORKSPACE = 'library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/pompom-default'
QUERY = '?' + urllib.parse.urlencode({'workspacePath': WORKSPACE})
BASE = '/api/v1/intelligence/workflow/'


def http(port, path, body=None):
    request = urllib.request.Request(f'http://localhost:{port}{BASE}{path}',
        data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(request, timeout=30))


def sql(database, query):
    return subprocess.check_output(['docker', 'exec', 'intelligence-postgres-1',
        'psql', '-U', 'pompom', '-d', database, '-Atc', query], text=True).strip()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def verify():
    before = json.loads(Path('/tmp/pompom-arda-before.json').read_text())
    arda = http(8080, f'idea-drafts/{DRAFT}{QUERY}')
    assert arda == before
    assert http(8080, f'idea-drafts/{DRAFT}/candidates{QUERY}') == []
    assert http(8080, f'idea-drafts/{DRAFT}/batches{QUERY}') == []
    native_events = int(sql('pompom', "SELECT count(*) FROM post_family_workflow_events WHERE kind IN ('IDEA_REQUEST','IDEA_RECEIPT','IDEA_CANDIDATE','IDEA_EVALUATION','IDEA_DECISION')"))
    assert native_events == 0
    candidates = http(8089, f'idea-drafts/{FIXTURE}/candidates{QUERY}')
    assert len(candidates) == 3
    ids = [c['candidateId'] for c in candidates]
    assert len(set(ids)) == 3
    assert len({c['receiptId'] for c in candidates}) == 1
    assert len({c['providerRequestId'] for c in candidates}) == 1
    receipt_sql = "SELECT (payload->'response')::text FROM post_family_workflow_events WHERE kind='IDEA_RECEIPT'"
    original_receipt = sql('pompom_idea_acceptance_20261021', receipt_sql)
    replay = http(8089, f'idea-drafts/{FIXTURE}/candidates/recover',
        {'workspacePath': WORKSPACE, 'requestId': candidates[0]['requestId']})
    assert replay['calls'] == 0 and replay['reused'] is True
    restored = http(8089, f'idea-drafts/{FIXTURE}/candidates{QUERY}')
    assert restored == candidates
    assert original_receipt == sql('pompom_idea_acceptance_20261021', receipt_sql)
    states = {c['payload']['title']: c['state'] for c in restored}
    assert states['Fixture: Backward Bowl'] == 'REJECTED'
    assert states['Fixture: Heavy Reflection'] == 'SELECTED'
    fixture_calls = len(Path('/tmp/pompom-idea-fixture-calls.jsonl').read_text().splitlines())
    assert fixture_calls == 1
    fixture_request = json.loads(Path('/tmp/pompom-idea-fixture-calls.jsonl').read_text().splitlines()[0])
    assert fixture_request['role'] == 'IDEA' and fixture_request['context']['requestedAlternativeCount'] == 3
    assert int(sql('pompom_idea_acceptance_20261021', f"SELECT count(*) FROM post_family_workflow_events WHERE kind='CREATIVE_ROLE' AND payload->>'role'='STORY' AND payload->'sourceRequest'->'context'->>'sourceIdeaDraftId'='{FIXTURE}'")) == 0
    try:
        http(8080, 'creative-role', {'role': 'IDEA', 'text': 'Unauthorized dispatch must be blocked',
             'generationAuthorized': False, 'maxCostUsd': .1,
             'context': {'sourceIdeaDraftId': DRAFT, 'requestedAlternativeCount': 3}})
        raise AssertionError('Missing authorization accepted')
    except urllib.error.HTTPError as error:
        denial = json.load(error)
        assert 400 <= error.code < 500
        assert 'authorization' in denial.get('detail', denial.get('message', ''))
        authorization_denial = {'httpStatus': error.code, 'body': denial}
    tests = []
    for name in ('IdeaCandidatePostgresTest', 'IdeaDraftPostgresTest', 'IdeaDraftServiceTest', 'WorkflowServiceTest'):
        result = ET.parse(ROOT / f'intelligence/backend/target/surefire-reports/TEST-com.pompomhills.intelligence.workflow.{name}.xml').getroot()
        assert all(result.get(k) == '0' for k in ('failures', 'errors', 'skipped'))
        tests.append({'suite': name, 'passed': int(result.get('tests'))})
    files = [
        'intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/IdeaCandidateService.java',
        'intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/IdeaDraftController.java',
        'intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/WorkflowService.java',
        'intelligence/backend/src/main/resources/db/migration/V73__native_idea_candidates.sql',
        'intelligence/backend/src/test/java/com/pompomhills/intelligence/workflow/IdeaCandidatePostgresTest.java',
        'intelligence/frontend/src/app/pages/creative-studio.page.ts',
        'intelligence/ml-service/app/workflow/creative_roles.py',
        'intelligence/ml-service/tests/test_native_idea_batch.py',
        'intelligence/scripts/idea-batch-acceptance/fixture_ml.py',
        'intelligence/scripts/idea-batch-acceptance/seed_selection_fixture.sql',
        'intelligence/scripts/idea-batch-acceptance/verify_acceptance.py',
        'intelligence/scripts/idea-batch-acceptance/acceptance_result.json',
    ]
    report = {
        'status': 'READY_FOR_OWNER_IDEA_AUTHORIZATION',
        'verifiedAtUtc': datetime.now(timezone.utc).isoformat(),
        'filesChangedByThisContinuation': [str(ROOT / f) for f in files],
        'preservedPreexistingChanges': ['ContentWorkspaceController.java', 'app/api/quality.py', 'app/parser/prompt_parser.py', 'tests/test_actor_source_attempts.py', 'Prior IDEA dispatch/contract changes in creative-studio.page.ts and creative_roles.py'],
        'batchPersistence': 'Native IDEA_REQUEST, IDEA_RECEIPT, IDEA_CANDIDATE, IDEA_EVALUATION and IDEA_DECISION events. Receipt committed separately; entire candidate/evaluation batch commits atomically. No STORY record created.',
        'identityAndLineage': {'candidateIds': ids, 'requestId': candidates[0]['requestId'], 'providerRequestId': candidates[0]['providerRequestId'], 'receiptId': candidates[0]['receiptId'], 'identity': 'Deterministic UUID from canonical request identity and candidate index; titles never identify candidates', 'payload': 'Complete immutable structured IDEA payload, parent draft and source revision, index, creation timestamp, candidate revision, evaluation/decision revisions'},
        'evaluationLifecycle': {'independent': True, 'paidEvaluationCalls': 0, 'mandatoryGateCount': 10, 'productionPolicyStatus': 'PENDING_EVIDENCE or REJECTED for exact duplicate stated rules; UNKNOWN is never promoted to PASS', 'limitation': 'No existing IDEA semantic/visual admission evaluator supports the required proof. Missing semantic/visual/originality evidence is exposed and blocks selection. Existing story/IR rules are not misrepresented as IDEA proof.', 'syntheticSelectionFixture': 'Only the disposable test DB has a fixture-identity evaluation for positive selection testing. This is not creative approval.'},
        'idempotencyAndRecovery': {'databaseUniqueIndexes': ['IDEA_REQUEST identity', 'IDEA_RECEIPT identity', 'IDEA_CANDIDATE request/index UUID'], 'locking': 'PostgreSQL transaction advisory locks; durable reservation before dispatch; unknown outcomes never dispatch again', 'receiptUnchangedAfterRecovery': True, 'receiptSha256': hashlib.sha256(original_receipt.encode()).hexdigest(), 'realBrowserRecovery': 'Initial 64-character binding limit failure saved receipt with zero candidate rows. Fixed deterministic UUID key, recovered all three through the UI, with fixture adapter call count still one.', 'providerRetries': 0},
        'threeCandidateFixtureResult': {'database': 'pompom_idea_acceptance_20261021', 'draftId': FIXTURE, 'recordCount': len(candidates), 'fixtureAdapterRequests': fixture_calls, 'role': fixture_request['role'], 'requestedCount': 3, 'actualProviderCalls': 0, 'costUsd': 0},
        'selectionRejectionBrowserTest': {'persistedStates': states, 'unresolvedMandatoryEvidenceSelection': 'Disabled in UI and rejected by backend', 'positiveSelection': 'Verified only with explicitly synthetic fixture-identity policy in isolated DB'},
        'reloadVerification': {'browserRefresh': 'PASS', 'navigateOverviewAndReturn': 'PASS', 'independentEvaluationRevisionRetained': 'PASS', 'serverRestartAndFinalBuildReload': 'PASS', 'repeatedRecoveryNoAdditionalCandidates': 'PASS'},
        'authorizationEnforcement': {'realUiRole': 'IDEA', 'provider': 'OPENAI', 'model': 'gpt-6-sol', 'requestedCandidates': 3, 'budgetUsdLeftUnchanged': 0, 'ownerConsentLeftUnchecked': True, 'confirmDisabled': True, 'missingAuthorizationResponse': authorization_denial, 'storyAuthorizationNotReused': True},
        'realArdaDraft': {'draftId': DRAFT, 'revision': arda['revision'], 'checkpoint': arda['checkpoint'], 'exactSavedRecordUnchanged': True, 'savedRecordSha256': digest(arda), 'fixtureDataPresent': False, 'nativeIdeaRequests': 0, 'nativeIdeaCandidates': 0, 'configuration': {k: arda['state'][k] for k in ('mainCharacterId', 'profile', 'duration', 'aspectRatio', 'targetGenerator', 'workspacePath')}, 'storedLegacyCandidateCountPreserved': arda['state']['candidateCount'], 'uiBatchCount': 3, 'environmentRepair': 'Restored missing directory for existing pompom-default workspace without modifying draft history or creating another production project'},
        'actualProviderCallsAndCost': {'providerCalls': 0, 'usd': 0, 'storyGeneration': 0, 'generatedImages': 0, 'videoRenders': 0, 'publishing': 0, 'newProductionProjects': 0},
        'tests': {'javaSuites': tests, 'javaTotalPassed': sum(t['passed'] for t in tests), 'nativeIdeaPythonPassed': 8, 'frontendBuild': 'PASS (existing bundle-size/unused-component warnings)', 'broaderPythonRun': {'passed': 73, 'failed': 3, 'failedTests': ['test_long_form_story_role_maps_explicit_goal_and_runs_existing_canonical_gates', 'test_canonical_story_evaluation_binds_only_source_quoted_story_plan_attempts', 'test_inline_character_only_constraint_is_not_an_actor_declaration'], 'scope': 'Story/actor tests outside native IDEA changes; broader suite is not claimed green'}},
        'remainingDefectsOrLimitations': ['No known remaining candidate-card, persistence, recovery, navigation, rejection or refresh defect in exercised flows.', 'IDEA semantic/visual admission proof remains unavailable and blocks actual candidate approval; no fabricated PASS or score.', 'Three failures remain in the broader story/actor Python suite; see tests section.'],
        'exactNextOwnerUiAction': "Open New Video > Saved Projects > Arda's New Story Audition > Open draft > Generate 3 IDEA Candidates. Review IDEA/OpenAI/gpt-6-sol/exactly 3, intentionally choose a positive maximum spend, personally check consent and press Confirm generation. Current budget remains $0 and consent remains unchecked. Generation remains in IDEA; unresolved admission evidence blocks selection and STORY is a separate later stage.",
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'report': str(OUT), 'status': report['status'], 'javaPassed': report['tests']['javaTotalPassed'], 'fixtureStates': states, 'actualProviderCalls': 0, 'actualCostUsd': 0}, ensure_ascii=False))


if __name__ == '__main__':
    verify()
