#!/usr/bin/env bash
set -euo pipefail

# Preparation only. This script reconstructs and snapshots the exact P2 source,
# compiles real-adapter requests, and leaves every paid dispatch gate disabled.
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
marker="$(mktemp "${TMPDIR:-/tmp}/pompom-real-preflight-marker-XXXXXX")"
trap 'rm -f "$marker"' EXIT

if [[ "${POMPOM_SKIP_FOCUSED_TESTS:-0}" != 1 ]]; then
  (cd "$root/ml-service" && PYTHONPATH="$root/ml-service" POMPOM_DATA_ROOT="$root/data" \
    .venv/bin/pytest -q tests/test_optimization_loop.py tests/test_adaptive_optimization_v3.py)
  (cd "$root/backend" && mvn -q -Dtest=OptimizationLoopTest test)
fi
"$root/scripts/acceptance-story-firstframe.sh" --real-provider-preflight

result_file="$(find "$root/backend/target/disposable-owner-http" -name result.json -newer "$marker" -print | sort | tail -1)"
[[ -n "$result_file" ]]
result_dir="$(dirname "$result_file")"

POMPOM_ROOT="$root" POMPOM_RESULT_DIR="$result_dir" python3 - <<'PY'
import hashlib,json,os
from pathlib import Path
root=Path(os.environ['POMPOM_ROOT']); folder=Path(os.environ['POMPOM_RESULT_DIR'])
outer=json.loads((folder/'result.json').read_text()); backend=json.loads((folder/'backend-http.json').read_text())
p=backend['storyFeasibility']['positiveCase']; pre=p['researchPreflight']; scope=pre['scope']; plan=pre['researchComparisonPlan']
expected={'story':'ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d','prompt':'1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5','settings':'e6aedfab391d7ee0a7e753b3dc8f4e8d57c31d8b2ada4b9f8b130b95b2689937'}
actual={'story':scope['approvedStorySha256'],'prompt':scope['baselineSha256'],'settings':scope['settingsSha256']}
assert actual==expected, {'expected':expected,'actual':actual}
assert p['canonical']['rulesetVersion']=='1.11' and abs(p['canonical']['score']-93.42708333333334)<1e-12 and p['canonical']['grade']=='A'
assert len(plan['runs'])==2 and plan['maximumRequests']==6 and plan['providerCalls']==0
operations=[op for run in plan['runs'] for op in run['operations']]
assert all(op['transportOrigin']=='REAL_PROVIDER_ADAPTER' and op['providerAdapter']=='CreativeCapabilityProvider' and op['fixtureFallbackAllowed'] is False and op['providerDispatched'] is False for op in operations)
assert {run['mode'] for run in plan['runs']}=={'DEEPSEEK_ONLY','OPENAI_ONLY'}

secrets={}
for source in (root/'backend/.env',root/'ml-service/.env'):
    if source.is_file():
        for line in source.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k,v=line.split('=',1)
                if k in ('OPENAI_API_KEY','DEEPSEEK_API_KEY') and v.strip(): secrets[k]=v.strip().strip('"').strip("'")
assert set(secrets)=={'OPENAI_API_KEY','DEEPSEEK_API_KEY'}
credential_file=folder/'provider-credentials.env'
credential_file.write_text(''.join(f'{k}={secrets[k]}\n' for k in sorted(secrets)))
credential_file.chmod(0o600)

catalog=json.loads((root/'data/workflow/creative-provider-profiles-v3.json').read_text())
allowlist=sorted({v['baseUrl'] for v in catalog['profiles'].values()})
network={'version':'disposable-real-provider-egress-v1','mode':'DENY_BY_DEFAULT','allowedHttpsOrigins':allowlist,'allowedInternal':['loopback-disposable-backend','loopback-disposable-ml','disposable-postgres-network-only'],'productionDatabaseReachable':False,'productionApiCredentialsPresent':False,'unrelatedExternalDestinationsAllowed':False}
(folder/'network-policy.json').write_text(json.dumps(network,indent=2)+'\n')
generation=next(op for op in operations if op['role']=='GENERATION')
manifest={
 'environment':'DEDICATED_DISPOSABLE_REAL_PROVIDER','preparationOnly':True,'executionEnabled':False,
 'databaseSnapshot':backend['restorableDatabaseSnapshot'],'dataRootSnapshot':backend['restorableDataRoot'],'ownerCredentialFile':backend['privateOwnerCredential'],'providerCredentialFile':str(credential_file),
 'contentId':scope['contentId'],'storyId':scope['approvedStory']['storyId'],'storyRevision':scope['approvedStory']['revision'],'storyApprovalRecordId':scope['approvedStory']['approvalRecordId'],'promptVersionId':scope['promptVersionId'],'analysisId':scope['analysisId'],'productionSettingsRecordId':p['preflight']['productionSettingsRecordId'],
 'storySha256':actual['story'],'promptSha256':actual['prompt'],'settingsSha256':actual['settings'],'sourceScopeSha256':pre['scopeSha256'],'instructionContextSha256':generation['instructionContextSha256'],
 'canonical':{'rulesetVersion':p['canonical']['rulesetVersion'],'score':p['canonical']['score'],'grade':p['canonical']['grade']},
 'creativeValidity':p['handoffRun']['progress']['promptHandoff']['creativeValidityAssessment'],
 'researchEligibility':p['preflight']['researchGenerationEligibility'],'plan':plan,
 'providerConfiguration':{k:{x:v[x] for x in ('provider','model','baseUrl','responseMode','contextTokens','inputUsdPerMillion','outputUsdPerMillion')} for k,v in catalog['profiles'].items()},
 'credentialPresence':{'deepseek':True,'openai':True},'networkPolicyFile':str(folder/'network-policy.json'),
 'fixtureBaselineTransport':'DETERMINISTIC_FIXTURE','fixtureDispatchClosedForExperiment':True,'realProviderRequests':0,'actualProviderSpendUsd':0,'actualReviewExecution':'NOT_EXECUTED'
}
(folder/'execution-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'evidenceDirectory':str(folder),'manifest':str(folder/'execution-manifest.json'),'realProviderRequests':0,'executionEnabled':False}))
PY

# Prove the snapshot is usable without touching the production database.
(
  restore_name="pompom-disposable-restore-$$"
  trap 'docker rm -f "$restore_name" >/dev/null 2>&1 || true' EXIT
  docker run -d --name "$restore_name" -e POSTGRES_DB=disposable_owner_http \
    -e POSTGRES_USER=disposable_owner_http -e POSTGRES_PASSWORD=restore-only postgres:17-alpine >/dev/null
  ready=false
  for _ in {1..100}; do if docker exec "$restore_name" pg_isready -U disposable_owner_http -d disposable_owner_http >/dev/null 2>&1; then ready=true; break; fi; sleep .2; done
  [[ "$ready" == true ]]; sleep 1
  docker cp "$result_dir/disposable-real-provider.dump" "$restore_name":/tmp/snapshot.dump >/dev/null
  docker exec "$restore_name" pg_restore -U disposable_owner_http -d disposable_owner_http --clean --if-exists /tmp/snapshot.dump
  POMPOM_RESTORE_CONTAINER="$restore_name" POMPOM_RESULT_DIR="$result_dir" python3 - <<'PYRESTORE'
import json,os,subprocess
name=os.environ['POMPOM_RESTORE_CONTAINER'];folder=os.environ['POMPOM_RESULT_DIR'];manifest=json.load(open(folder+'/execution-manifest.json'))
def q(sql): return subprocess.check_output(['docker','exec',name,'psql','-U','disposable_owner_http','-d','disposable_owner_http','-Atc',sql],text=True).strip()
e={'database':q('select current_database()'),'flywayVersion':q("select version from flyway_schema_history where success=true order by installed_rank desc limit 1"),'contentCount':int(q('select count(*) from contents')),'promptVersionCount':int(q('select count(*) from prompt_versions')),'workflowRecordCount':int(q('select count(*) from post_family_workflow_events')),'optimizationRunCount':int(q('select count(*) from optimization_runs')),'optimizationRequestCount':int(q('select count(*) from optimization_run_requests')),'productionDatabaseWrites':0,'realProviderRequests':0,'restoredAnalysisPresent':q("select count(*) from post_family_workflow_events where id='"+manifest['analysisId']+"'")=='1','restoredStoryPresent':q("select count(*) from post_family_workflow_events where id='"+manifest['storyId']+"'")=='1'}
assert e['database']=='disposable_owner_http' and e['flywayVersion']=='70' and e['restoredAnalysisPresent'] and e['restoredStoryPresent'];assert e['optimizationRunCount']==e['optimizationRequestCount']==0
open(folder+'/restore-verification.json','w').write(json.dumps(e,indent=2)+'\n')
PYRESTORE
)

echo "Preparation evidence: $result_dir"
echo 'STOPPED_BEFORE_PROVIDER_DISPATCH=YES'
