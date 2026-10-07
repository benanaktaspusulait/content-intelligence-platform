#!/usr/bin/env bash
# Opt-in paid OpenArt -> Pompom end-to-end smoke test.
set -euo pipefail

: "${OPENART_LIVE_TEST:?Set OPENART_LIVE_TEST=true to enable the paid smoke test}"
[[ "$OPENART_LIVE_TEST" == "true" ]] || { echo "OPENART_LIVE_TEST must be true" >&2; exit 1; }
: "${OPENART_LIVE_CONFIRM:?Set OPENART_LIVE_CONFIRM=SPEND_CREDITS to authorize provider spend}"
[[ "$OPENART_LIVE_CONFIRM" == "SPEND_CREDITS" ]] || { echo "OPENART_LIVE_CONFIRM must equal SPEND_CREDITS" >&2; exit 1; }
: "${POMPOM_LIVE_CONTENT_ID:?Set POMPOM_LIVE_CONTENT_ID}"
: "${POMPOM_LIVE_PROMPT_VERSION_ID:?Set POMPOM_LIVE_PROMPT_VERSION_ID}"
: "${POMPOM_LIVE_VALIDATION_RECORD_ID:?Set POMPOM_LIVE_VALIDATION_RECORD_ID}"

BASE_URL="${POMPOM_RENDER_BASE_URL:-http://localhost:4200}"
MODEL="${OPENART_LIVE_MODEL:-byte-plus-seedance-2-mini}"
DURATION="${OPENART_LIVE_DURATION:-5}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

HOME="${HOME:-$HOME}" openart account --json --select credits,plan,workspace >"$TMP_DIR/account.json"
HOME="${HOME:-$HOME}" openart model cost --model "$MODEL" --mode text2video --json >"$TMP_DIR/price.json"
echo "OpenArt account and model quote verified:"
jq '{plan,credits,workspace,price: .}' "$TMP_DIR/account.json" "$TMP_DIR/price.json" 2>/dev/null || true

IDEMPOTENCY_KEY="openart-live-$(uuidgen | tr '[:upper:]' '[:lower:]')"
JOB_RESPONSE="$(curl -fsS -X POST "$BASE_URL/api/v1/render-jobs" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d "$(jq -n \
    --argjson contentId "$POMPOM_LIVE_CONTENT_ID" \
    --argjson promptVersionId "$POMPOM_LIVE_PROMPT_VERSION_ID" \
    --argjson validationRecordId "$POMPOM_LIVE_VALIDATION_RECORD_ID" \
    --arg model "$MODEL" \
    --argjson duration "$DURATION" \
    '{contentId:$contentId,promptVersionId:$promptVersionId,validationRecordId:$validationRecordId,jobType:"VIDEO",openartModel:$model,openartParams:{durationSeconds:$duration,aspectRatio:"16:9"},requestPromptSha256:null}')")"
JOB_ID="$(jq -r '.renderJobId' <<<"$JOB_RESPONSE")"
[[ -n "$JOB_ID" && "$JOB_ID" != "null" ]] || { echo "Queue response did not contain renderJobId" >&2; exit 1; }
echo "Queued render job: $JOB_ID"

for _ in $(seq 1 240); do
  JOB="$(curl -fsS "$BASE_URL/api/v1/render-jobs/$JOB_ID")"
  STATUS="$(jq -r '.status' <<<"$JOB")"
  echo "status=$STATUS"
  case "$STATUS" in
    COMPLETE) break ;;
    FAILED|ABANDONED) echo "$JOB"; exit 1 ;;
  esac
  sleep 5
done

FINAL_STATUS="$(jq -r '.status' <<<"$JOB")"
[[ "$FINAL_STATUS" == "COMPLETE" ]] || { echo "Timed out waiting for render completion" >&2; exit 1; }
ASSET_ID="$(jq -r '.attempts[-1].assetId' <<<"$JOB")"
[[ -n "$ASSET_ID" && "$ASSET_ID" != "null" ]] || { echo "Completed job has no assetId" >&2; exit 1; }

curl -fsS -D "$TMP_DIR/headers" -o "$TMP_DIR/final.mp4" "$BASE_URL/api/v1/render-assets/$ASSET_ID/download"
grep -qi '^content-type: video/' "$TMP_DIR/headers"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height \
  -of csv=p=0 "$TMP_DIR/final.mp4" | grep -Eq '^1920,1080$'
echo "OpenArt paid E2E passed: job=$JOB_ID asset=$ASSET_ID final=1920x1080"
