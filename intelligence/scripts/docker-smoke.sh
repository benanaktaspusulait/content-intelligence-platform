#!/bin/bash
# Deterministic Docker Compose smoke test for Pompom Creative Intelligence.
#
# Builds every target service from a clean image, starts the stack, waits for
# container health, and asserts the ML quality router and both Spring services
# are reachable. Always tears the stack down, even on failure.
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$APP/docker-compose.yml")

cleanup() {
  echo "== docker-smoke: tearing down =="
  "${COMPOSE[@]}" down -v --remove-orphans || true
}
trap cleanup EXIT

echo "== docker-smoke: validating compose config =="
"${COMPOSE[@]}" config --quiet

echo "== docker-smoke: building images =="
"${COMPOSE[@]}" build

echo "== docker-smoke: starting stack and waiting for container health =="
# backend and creative-render-service each define a Docker HEALTHCHECK against
# their Spring Actuator /actuator/health endpoint (see their Dockerfiles and the
# service definitions in docker-compose.yml). `--wait` blocks here until every
# service with a healthcheck reports healthy, so by the time this returns the
# Spring context has actually finished booting (not just "container started").
"${COMPOSE[@]}" up -d --wait

echo "== docker-smoke: ML quality router health =="
curl --fail --silent --show-error "http://localhost:8000/health" >/dev/null
curl --fail --silent --show-error "http://localhost:8000/api/v1/quality/health" >/dev/null
curl --fail --silent --show-error "http://localhost:8000/health/ready" >/dev/null

# `assert_http_server_up` fails the gate only on a connection-level failure
# (the container/port is not listening); it does not require a specific HTTP
# status, since a route that is unauthenticated-only, not-yet-implemented, or a
# 404 on a path that lives on a different service legitimately returns a
# non-2xx status from a server that is otherwise correctly up and healthy.
assert_http_server_up() {
  local name="$1" url="$2"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out "%{http_code}" "$url")"
  echo "   $name -> HTTP $status"
  if [ "$status" = "000" ]; then
    echo "docker-smoke: $name did not respond (connection failure) at $url" >&2
    return 1
  fi
}

echo "== docker-smoke: intelligence backend reachable =="
assert_http_server_up "backend" "http://localhost:8080/api/v1/render-jobs"

echo "== docker-smoke: creative render service reachable =="
assert_http_server_up "creative-render-service" "http://localhost:8081/actuator/health"

echo "== docker-smoke: frontend reachable =="
curl --fail --silent --show-error "http://localhost:4200" >/dev/null

echo "== docker-smoke: all checks passed =="
