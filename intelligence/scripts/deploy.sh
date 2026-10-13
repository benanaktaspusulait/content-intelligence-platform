#!/usr/bin/env bash
# Build current sources and deploy the local intelligence application services.
set -Eeuo pipefail

stack_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$stack_dir"
compose=(docker compose --project-directory "$stack_dir" -f "$stack_dir/docker-compose.yml")
mode=deploy
selected=()

usage() {
  cat <<'EOF'
Usage: ./intelligence/scripts/deploy.sh [--dry-run | --check] [SERVICE ...]

No services specified: build and deploy ml-service, backend and frontend.
Services: ml-service backend frontend
  --dry-run  Print the build/deploy plan without changing anything.
  --check    Check running containers and read-only HTTP endpoints only.
  --help     Show this help.

Examples:
  ./intelligence/scripts/deploy.sh
  ./intelligence/scripts/deploy.sh ml-service
  ./intelligence/scripts/deploy.sh backend
  ./intelligence/scripts/deploy.sh --check

Backend deployment also restarts frontend so nginx resolves its new address.
Existing PostgreSQL and creative-render-service must already be running.
Builds use the repository Dockerfiles (their normal test-skipping build steps).
No evaluation, generation, publication, database reset, commit or push is run.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --help|-h) usage; exit 0 ;;
    --dry-run|--check)
      [[ "$mode" == deploy ]] || { echo 'Choose only one mode.' >&2; exit 2; }
      mode="${arg#--}" ;;
    ml-service|backend|frontend) selected+=("$arg") ;;
    *) echo "Unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done
if [[ ${#selected[@]} -eq 0 ]]; then selected=(ml-service backend frontend); fi

contains() {
  local wanted="$1" item
  for item in "${selected[@]}"; do [[ "$item" != "$wanted" ]] || return 0; done
  return 1
}
build_services=()
run_services=()
for service in ml-service backend frontend; do
  if contains "$service"; then build_services+=("$service"); run_services+=("$service"); fi
done
if contains backend && ! contains frontend; then run_services+=(frontend); fi

print_command() { printf '  '; printf '%q ' "$@"; printf '\n'; }
if [[ "$mode" == dry-run ]]; then
  echo "Compose directory: $stack_dir"
  print_command "${compose[@]}" build "${build_services[@]}"
  print_command "${compose[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 180 "${run_services[@]}"
  echo 'Then check container health, image IDs and read-only HTTP responses.'
  exit 0
fi

command -v docker >/dev/null || { echo 'Docker is required.' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Start Docker Desktop first.' >&2; exit 1; }
"${compose[@]}" version >/dev/null
"${compose[@]}" config --quiet

require_running() {
  local service="$1" id status health
  id="$("${compose[@]}" ps -q "$service")"
  [[ -n "$id" ]] || { echo "Required service is not running: $service" >&2; return 1; }
  status="$(docker inspect --format '{{.State.Status}}' "$id")"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")"
  [[ "$status" == running && ( "$health" == healthy || "$health" == none ) ]] || {
    echo "$service is not ready: $status / $health" >&2; return 1;
  }
}

if [[ "$mode" == deploy ]]; then
  # --no-deps deliberately leaves database and generation/publication services alone.
  if contains backend; then
    require_running postgres
    if ! contains ml-service; then require_running ml-service; fi
  fi
  for service in "${run_services[@]}"; do
    if [[ "$service" == frontend ]]; then
      require_running creative-render-service
      if ! contains backend; then require_running backend; fi
    fi
  done
  echo "Building current sources: ${build_services[*]}"
  "${compose[@]}" build "${build_services[@]}"
  echo "Deploying: ${run_services[*]}"
  "${compose[@]}" up -d --no-deps --force-recreate --wait --wait-timeout 180 "${run_services[@]}"
fi

check_http() {
  local service="$1" port="$2" path="$3" published host_port
  published="$("${compose[@]}" port "$service" "$port" | head -n 1)"
  host_port="${published##*:}"
  [[ "$host_port" =~ ^[0-9]+$ ]] || { echo "No published port for $service:$port" >&2; return 1; }
  curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
    "http://localhost:$host_port$path" >/dev/null
  echo "  $service HTTP check passed ($path)"
}

for service in "${run_services[@]}"; do
  require_running "$service"
  id="$("${compose[@]}" ps -q "$service")"
  running_image="$(docker inspect --format '{{.Image}}' "$id")"
  image_tag="$(docker inspect --format '{{.Config.Image}}' "$id")"
  built_image="$(docker image inspect --format '{{.Id}}' "$image_tag")"
  [[ "$running_image" == "$built_image" ]] || { echo "$service still runs an older image; redeploy it." >&2; exit 1; }
  echo "  $service: $running_image"
  case "$service" in
    ml-service) check_http "$service" 8000 /health ;;
    backend) check_http "$service" 8080 /actuator/health ;;
    frontend)
      check_http "$service" 80 /
      check_http "$service" 80 /api/v1/intelligence/workflow/provider-capabilities ;;
  esac
done
"${compose[@]}" ps "${run_services[@]}"
echo 'Verified. Application: http://localhost:4200'
