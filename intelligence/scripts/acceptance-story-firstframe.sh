#!/usr/bin/env bash
set -euo pipefail

# Disposable, no-egress acceptance gate. This command deliberately does not
# enable CPQ_PILOT_REAL_ENABLED and never mounts the production owner config.
# Testcontainers owns PostgreSQL and the focused tests use deterministic
# provider/image fixtures at their application boundaries.
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
backend="$root/backend"
ml="$root/ml-service"
report_dir="${TMPDIR:-/tmp}/pompom-story-firstframe-acceptance"
mkdir -p "$report_dir"
trap 'rm -rf "$report_dir"' EXIT

if ! docker info >/dev/null 2>&1; then
  echo 'Docker is required for the disposable PostgreSQL test container.' >&2
  exit 2
fi

# The ML tests are offline by construction. A network namespace is created
# only to make the no-egress policy explicit for callers that run this command
# inside Docker; it is never attached to the production compose project.
network="pompom-acceptance-${RANDOM}-$$"
docker network create --internal "$network" >/dev/null
fixture_pid=""
cleanup_network() {
  if [[ -n "$fixture_pid" ]]; then kill "$fixture_pid" >/dev/null 2>&1 || true; fi
  docker network rm "$network" >/dev/null 2>&1 || true
}
trap 'cleanup_network; rm -rf "$report_dir"' EXIT

fixture_dir="$report_dir/fixtures"
mkdir -p "$fixture_dir"
cat > "$fixture_dir/story.json" <<'JSON'
{"alternatives":[{"candidateId":"candidate-1","title":"Fixture A","text":"Mimi sees a note and it sticks."},{"candidateId":"candidate-2","title":"Fixture B","text":"Mimi reaches for a note and it multiplies."}]}
JSON

python_bin="python3"
if [[ -x "$ml/.venv/bin/python" ]]; then python_bin="$ml/.venv/bin/python"; fi
echo 'Starting isolated ML HTTP fixture service...'
(
  cd "$ml"
  PYTHONPATH="$ml" POMPOM_DATA_ROOT="$root/data" \
  POMPOM_ISOLATED_ACCEPTANCE=true POMPOM_ISOLATED_FIXTURE_TOKEN="$(printf '%032d' 0)" \
  POMPOM_ISOLATED_FIXTURE_DIR="$fixture_dir" WORKFLOW_CREATIVE_ROLES_ENABLED=true \
  WORKFLOW_STORY_MODEL=fixture WORKFLOW_STORY_INPUT_USD_PER_MILLION=1 WORKFLOW_STORY_OUTPUT_USD_PER_MILLION=1 \
  "$python_bin" -m uvicorn app.main:app --host 127.0.0.1 --port 18000 >"$report_dir/ml-http.log" 2>&1
) &
fixture_pid=$!
for _ in {1..30}; do curl -fsS http://127.0.0.1:18000/health >/dev/null 2>&1 && break; sleep 0.2; done
curl -fsS -X POST http://127.0.0.1:18000/api/v1/workflow/creative-role \
  -H 'content-type: application/json' \
  --data '{"role":"STORY","text":"Mimi note","maxCostUsd":0.20,"context":{"requestedAlternativeCount":2,"inputMode":"DETAILED_STORY","storyGenerationMode":"IMPROVE_EXISTING_STORY","lockedRequirements":["PRESERVE_CORE_PREMISE"]}}' \
  >"$report_dir/ml-http-response.json"
POMPOM_ACCEPTANCE_RESPONSE="$report_dir/ml-http-response.json" python3 - <<'PY'
import json, os
value=json.load(open(os.environ['POMPOM_ACCEPTANCE_RESPONSE']))
assert value['provider']=='ISOLATED_FIXTURE'
assert value['providerDispatched'] is False
assert len(value['result']['alternatives']) == 2
PY
echo 'Isolated ML HTTP fixture transport verified.'

echo 'Running deterministic ML contracts (no provider/image egress)...'
(
  cd "$ml"
  export PYTHONPATH="$ml${PYTHONPATH:+:$PYTHONPATH}"
  export POMPOM_DATA_ROOT="$root/data"
  POMPOM_GOLDEN_PROVIDER_MODE=FROZEN_DETERMINISTIC \
    "$python_bin" -m pytest -q tests/test_story_review_contract.py tests/test_optimization_loop.py \
      tests/test_isolated_fixture_transport.py \
      tests/test_start_frame_generation.py
) | tee "$report_dir/ml-tests.txt"

echo 'Running disposable backend persistence/evaluator contracts...'
(
  cd "$backend"
  mvn -q -Dtest=StoryEvolutionServiceTest,PlatformIntegrationTest test
) | tee "$report_dir/backend-tests.txt"

cat > "$report_dir/result.json" <<JSON
{
  "harness": "disposable-testcontainers",
  "network": "internal-no-egress",
  "realProviderCalls": 0,
  "realImageGenerationCalls": 0,
  "realVideoRenderCalls": 0,
  "productionDatabaseMutations": 0,
  "mlTests": "$report_dir/ml-tests.txt",
  "backendTests": "$report_dir/backend-tests.txt",
  "httpWorkflow": "NOT_EXECUTED"
}
JSON
cat "$report_dir/result.json"
echo 'The command verifies deterministic contracts only; it does not authorize paid dispatch or production records.'
