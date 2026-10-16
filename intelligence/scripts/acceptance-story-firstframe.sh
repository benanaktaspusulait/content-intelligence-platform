#!/usr/bin/env bash
set -euo pipefail

# Required P0 checkpoint: real disposable Spring HTTP, owner auth and approved source.
# This command does not claim the later Story -> A prompt -> first-frame chain passed.
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
backend="$root/backend"
ml="$root/ml-service"

# Preserve only runtime locations, not provider keys, production DB config or owner secrets.
if [[ "${POMPOM_ACCEPTANCE_CLEAN_ENV:-}" != 1 ]]; then
  exec env -i PATH="$PATH" HOME="$HOME" \
    JAVA_HOME="${JAVA_HOME:-}" TMPDIR="${TMPDIR:-/tmp}" \
    POMPOM_ACCEPTANCE_CLEAN_ENV=1 /bin/bash "$0" "$@"
fi
mode="${1:---p0}"
if [[ "$mode" != --p0 && "$mode" != --components && "$mode" != --story-evolution && "$mode" != --story-feasibility && "$mode" != --real-provider-preflight ]]; then
  echo 'Usage: acceptance-story-firstframe.sh [--p0 | --story-evolution | --story-feasibility | --real-provider-preflight | --components]' >&2
  exit 2
fi
mkdir -p "$backend/target/disposable-owner-http"
result_dir="$(mktemp -d "$backend/target/disposable-owner-http/run-XXXXXX")"
runtime_dir="$(mktemp -d "${TMPDIR%/}/pompom-p0-XXXXXX")"
fixture_dir="$runtime_dir/fixtures"
fixture_pid=""
completed=false
cleanup() {
  task_exit=$?
  trap - EXIT
  set +e
  if [[ -n "$fixture_pid" ]]; then
    kill "$fixture_pid" >/dev/null 2>&1 || true
    wait "$fixture_pid" 2>/dev/null || true
  fi
  POMPOM_RESULT_DIR="$result_dir" POMPOM_EXIT_CODE="$task_exit" POMPOM_COMPLETED="$completed" POMPOM_MODE="$mode" \
    python3 - <<'PY'
import json, os
from pathlib import Path
folder=Path(os.environ['POMPOM_RESULT_DIR'])
result={'scope':{'--p0':'P0_DISPOSABLE_OWNER_HTTP','--story-evolution':'P1_STORY_EVOLUTION_HTTP','--story-feasibility':'P2_CANONICAL_A_AWARE_STORY_FEASIBILITY','--real-provider-preflight':'DISPOSABLE_REAL_PROVIDER_PREFLIGHT','--components':'COMPONENTS_ONLY'}[os.environ['POMPOM_MODE']],
        'harnessExitCode':int(os.environ['POMPOM_EXIT_CODE']),
        'p0HttpAcceptance':os.environ['POMPOM_COMPLETED']=='true',
        'p1Acceptance':os.environ['POMPOM_MODE']=='--story-evolution' and os.environ['POMPOM_COMPLETED']=='true',
        'p2Acceptance':os.environ['POMPOM_MODE'] in ('--story-feasibility','--real-provider-preflight') and os.environ['POMPOM_COMPLETED']=='true',
        'realProviderPreflight':os.environ['POMPOM_MODE']=='--real-provider-preflight' and os.environ['POMPOM_COMPLETED']=='true',
        'fullStoryPromptFirstFrameVerified':False,
        'realProviderCalls':0,'realImageCalls':0,'realRenderCalls':0,'productionDatabaseWrites':0}
for file,key in [('backend-http.json','backend'),('ml-egress.json','mlEgress'),('ml-http-response.json','mlFixtureResponse')]:
    p=folder/file
    if p.is_file(): result[key]=json.loads(p.read_text())
if result['p0HttpAcceptance'] and not result.get('mlEgress',{}).get('noExternalEgress',False):
    result['p0HttpAcceptance']=False
    result['p1Acceptance']=False
    result['p2Acceptance']=False
    result['harnessExitCode']=1
(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'resultFile':str(folder/'result.json'), 'exitCode':result['harnessExitCode'],
                  'p0HttpAcceptance':result['p0HttpAcceptance']}))
raise SystemExit(result['harnessExitCode'])
PY
  result_exit=$?
  if [[ -f "$fixture_dir/provider-trace.jsonl" ]]; then cp "$fixture_dir/provider-trace.jsonl" "$result_dir/provider-trace.jsonl"; fi
  rm -rf "$runtime_dir"
  exit "$result_exit"
}
trap cleanup EXIT

if ! docker info >/dev/null 2>&1; then
  echo 'Docker is required. P0 acceptance cannot be skipped.' >&2
  exit 2
fi
python_bin="$ml/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo 'The repository ML virtualenv is required; no dependencies will be installed automatically.' >&2
  exit 2
fi
fixture_dir="$runtime_dir/fixtures"
mkdir -p "$fixture_dir"
cat > "$fixture_dir/story.json" <<'JSON'
{"alternatives":[{"candidateId":"candidate-1","title":"Pip contact and consequence","text":"Pip the rabbit reaches for a toy cabinet with a sticky note. The note clings to Pip's finger instead. Peeling splits it into one note per hand. Each pull doubles the notes from two to four to eight. Pip sees the note-covered reflection in a mirror, gasps, then sneezes the notes onto the cabinet. Pip is relieved but the cabinet stays messy."},{"candidateId":"candidate-2","title":"Pip mirror reveal","text":"Pip the rabbit wants to mark a toy cabinet, but a sticky note catches on Pip's finger. Pip tries to remove it; both hands now carry a note. Pulling doubles the notes repeatedly and covers Pip. The mirror reveals the mess, and a startled gasp turns into a sneeze. The cabinet catches the flying notes, leaving Pip relieved beside a messy cabinet."}]}
JSON
if [[ "$mode" == --story-evolution ]]; then python3 "$root/scripts/acceptance-story-fixtures.py" "$fixture_dir"; fi
if [[ "$mode" == --story-feasibility || "$mode" == --real-provider-preflight ]]; then python3 "$root/scripts/acceptance-story-feasibility-fixtures.py" "$fixture_dir"; fi
fixture_token="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export WORKFLOW_ADAPTIVE_DISPATCH_TOKEN="$fixture_token"
(
  cd "$ml"
  export PYTHONPATH="$ml"
  export POMPOM_DATA_ROOT="$root/data"
  export POMPOM_ISOLATED_ACCEPTANCE=true
  export POMPOM_ISOLATED_FIXTURE_TOKEN="$fixture_token"
  export POMPOM_ISOLATED_FIXTURE_DIR="$fixture_dir"
  export WORKFLOW_CREATIVE_ROLES_ENABLED=true
  export CPQ_PILOT_REAL_ENABLED=false
  if [[ "$mode" == --real-provider-preflight ]]; then
    for secret_file in "$ml/.env" "$backend/.env"; do
      [[ -f "$secret_file" ]] || continue
      while IFS='=' read -r secret_name secret_value || [[ -n "$secret_name" ]]; do
        case "$secret_name" in OPENAI_API_KEY|DEEPSEEK_API_KEY) secret_value="${secret_value%\"}"; secret_value="${secret_value#\"}"; export "$secret_name=$secret_value";; esac
      done < "$secret_file"
    done
    [[ -n "${OPENAI_API_KEY:-}" && -n "${DEEPSEEK_API_KEY:-}" ]] || { echo 'Both provider credentials must be configured for real-provider preflight' >&2; exit 3; }
  fi
  exec "$python_bin" "$root/scripts/acceptance-ml-http.py" "$runtime_dir/ml-port" "$result_dir/ml-egress.json"
) >"$result_dir/ml-http.log" 2>&1 &
fixture_pid=$!
ml_url=""
for _ in {1..100}; do
  if ! kill -0 "$fixture_pid" 2>/dev/null; then
    echo "Isolated ML startup failed. Log: $result_dir/ml-http.log" >&2
    exit 1
  fi
  if [[ -s "$runtime_dir/ml-port" ]]; then
    ml_url="http://127.0.0.1:$(cat "$runtime_dir/ml-port")"
    if curl --noproxy '*' --max-time 1 -fsS "$ml_url/health" >"$result_dir/ml-health.json" 2>/dev/null; then break; fi
  fi
  sleep 0.1
done
[[ -n "$ml_url" ]]
curl --noproxy '*' --max-time 3 -fsS "$ml_url/health" >/dev/null
unsigned_status="$(curl --noproxy '*' --max-time 5 -sS -o "$result_dir/hmac-negative.json" -w '%{http_code}' -X POST "$ml_url/api/v1/workflow/creative-role" -H 'content-type: application/json' --data '{"role":"STORY","text":"must not dispatch","maxCostUsd":0.01,"context":{}}')"
[[ "$unsigned_status" == 403 ]]
POMPOM_ACCEPTANCE_ML_URL="$ml_url" "$python_bin" - <<'PYPROBE' >"$result_dir/ml-http-response.json"
import hashlib,hmac,json,os,urllib.request
body=json.dumps({'role':'STORY','text':'Pip and sticky notes','maxCostUsd':0.01,'context':{'requestedAlternativeCount':2,'inputMode':'DETAILED_STORY','storyGenerationMode':'IMPROVE_EXISTING_STORY'}}).encode()
signature=hmac.new(os.environ['WORKFLOW_ADAPTIVE_DISPATCH_TOKEN'].encode(),body,hashlib.sha256).hexdigest()
request=urllib.request.Request(os.environ['POMPOM_ACCEPTANCE_ML_URL']+'/api/v1/workflow/creative-role',data=body,headers={'Content-Type':'application/json','X-Adaptive-Dispatch':signature})
print(urllib.request.urlopen(request,timeout=10).read().decode())
PYPROBE
POMPOM_ACCEPTANCE_RESPONSE="$result_dir/ml-http-response.json" python3 - <<'PY'
import json, os
value=json.load(open(os.environ['POMPOM_ACCEPTANCE_RESPONSE']))
assert value['provider']=='ISOLATED_FIXTURE'
assert value['providerDispatched'] is False
assert value['calls']==0 and value['actualCostUsd']==0
assert len(value['result']['alternatives'])==2
PY

echo "Isolated FastAPI fixture connected: $ml_url"
echo "Evidence directory: $result_dir"
if [[ "$mode" == --components ]]; then
  (cd "$ml"; PYTHONPATH="$ml" POMPOM_DATA_ROOT="$root/data" \
    "$python_bin" -m pytest -q tests/test_story_review_contract.py tests/test_optimization_loop.py \
    tests/test_isolated_fixture_transport.py tests/test_start_frame_generation.py) \
    >"$result_dir/component-tests.log" 2>&1
  echo 'Component-only mode completed. P0 HTTP checkpoint was not executed in this mode.'
  # This mode is explicitly not advertised as a full acceptance success.
  exit 0
fi

echo 'Starting real disposable Spring HTTP + owner/source acceptance...'
(
  cd "$backend"
  mvn -q -Dtest=DisposableOwnerHttpAcceptanceTest \
    -Dpompom.acceptance=true \
    -Dpompom.acceptance.mode="$mode" \
    -Dpompom.acceptance.provider-trace="$fixture_dir/provider-trace.jsonl" \
    -Dpompom.acceptance.ml-url="$ml_url" \
    -Dpompom.acceptance.output="$result_dir/backend-http.json" \
    -DargLine=-Djava.security.manager=allow test
) >"$result_dir/backend-http.log" 2>&1 || {
  tail -45 "$result_dir/backend-http.log" >&2
  exit 1
}
# A skipped/empty test run, stale artifact, wrong database or partial result cannot pass.
POMPOM_RESULT_DIR="$result_dir" POMPOM_MODE="$mode" python3 - <<'PY'
import json, os
from pathlib import Path
folder=Path(os.environ['POMPOM_RESULT_DIR'])
v=json.loads((folder/'backend-http.json').read_text())
assert v['p0HttpAcceptance'] is True
if os.environ['POMPOM_MODE']=='--story-evolution':
    p=v['storyEvolution']
    assert p['p1Acceptance'] and p['roundsExecuted']==2 and p['newPromptId'] and p['analysisId']
    assert isinstance(p['canonical']['score'],(int,float)) and p['canonical']['rulesetVersion']=='1.11'
    assert p['hmacVerified'] and p['requestCount']==4
    assert p['actualCostUsd']==p['providerCalls']==0
if os.environ['POMPOM_MODE'] in ('--story-feasibility','--real-provider-preflight'):
    p=v['storyFeasibility']
    assert p['p2Acceptance'] and p['negativeCase']['state']=='STOPPED'
    assert p['negativeCase']['progress']['reason']=='NO_ELIGIBLE_STORY_CANDIDATE'
    assert p['positiveCase']['roundsExecuted']==2 and p['positiveCase']['newPromptId'] and p['positiveCase']['analysisId']
    assert p['positiveCase']['canonical']['rulesetVersion']=='1.11'
    assert p['positiveCase']['providerCalls']==p['positiveCase']['actualCostUsd']==0
    if os.environ['POMPOM_MODE']=='--real-provider-preflight':
        plan=p['positiveCase']['researchPreflight']['researchComparisonPlan']
        assert len(plan['runs'])==2 and plan['maximumRequests']==6 and plan['providerCalls']==0
        assert all(op['transportOrigin']=='REAL_PROVIDER_ADAPTER' and op['providerAdapter']=='CreativeCapabilityProvider' and op['fixtureFallbackAllowed'] is False and op['providerDispatched'] is False for run in plan['runs'] for op in run['operations'])
        assert Path(v['restorableDatabaseSnapshot']).is_file()
        credential=Path(v['privateOwnerCredential']); assert credential.is_file() and (credential.stat().st_mode & 0o777)==0o600
assert v['postgresDatabase']=='disposable_owner_http' and v['flywayVersion']=='70'
assert v['backendPort']>0 and v['ownerLoginHttp'] and v['ownerSession']
assert v['csrfAndOriginVerified'] and v['logoutRevocationVerified'] and v['rateLimitingVerified']
assert v['approvedStoryId'] and v['storyApprovalId'] and len(v['approvedStorySha256'])==64
assert v['mlFixtureConnected'] and v['unexpectedNetworkAttempts']==[]
role_trace=[json.loads(line) for line in (folder/'ml-role-http.jsonl').read_text().splitlines()]
assert role_trace and all(row['hmacVerified'] for row in role_trace)
assert json.loads((folder/'hmac-negative.json').read_text())['providerDispatched'] is False
assert all(x['status']==x['expectedStatus'] for x in v['httpTrace'])
assert v['realProviderCalls']==v['realImageCalls']==v['realRenderCalls']==v['productionDatabaseWrites']==0
audit=json.loads((folder/'ml-egress.json').read_text())
assert audit['negativeProbe']=='DENIED_BEFORE_DISPATCH' and audit['noExternalEgress']
PY
completed=true
if [[ "$mode" == --story-evolution ]]; then
  echo 'P1_ACCEPTANCE=YES. Actual new canonical score recorded; no A/A+ inference claim.'
elif [[ "$mode" == --story-feasibility ]]; then
  echo 'P2_ACCEPTANCE=YES. Story feasibility prediction and actual post-BUILD_PROMPT Ruleset 1.11 result recorded separately.'
elif [[ "$mode" == --real-provider-preflight ]]; then
  echo 'DISPOSABLE_REAL_PROVIDER_PREFLIGHT=YES. Restorable database and sealed no-dispatch plan recorded; execution remains disabled.'
else
  echo 'P0_HTTP_ACCEPTANCE=YES. Next operation: STORY_EVOLUTION_HTTP_START (fixture scope only).'
fi
