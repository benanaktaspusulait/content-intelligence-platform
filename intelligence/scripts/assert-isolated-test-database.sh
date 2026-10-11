#!/usr/bin/env bash
set -euo pipefail

# Fail closed before any persistent acceptance/integration test can run.
# Both URLs are required so the guard compares the actual server/database target,
# rather than trusting a database-name or environment-name convention.
: "${POMPOM_TEST_DATABASE_URL:?Set POMPOM_TEST_DATABASE_URL to the disposable test database}"
: "${POMPOM_APPLICATION_DATABASE_URL:?Set POMPOM_APPLICATION_DATABASE_URL to the normal application database}"

command -v psql >/dev/null 2>&1 || {
  echo "isolation guard: psql is required" >&2
  exit 2
}

target() {
  local url="$1"
  psql "$url" -X -Atqc "SELECT current_database() || '|' || COALESCE(inet_server_addr()::text, '') || '|' || inet_server_port()"
}

test_target="$(target "$POMPOM_TEST_DATABASE_URL")"
application_target="$(target "$POMPOM_APPLICATION_DATABASE_URL")"

if [[ -z "$test_target" || -z "$application_target" ]]; then
  echo "isolation guard: could not resolve both live database targets" >&2
  exit 2
fi

if [[ "$test_target" == "$application_target" ]]; then
  echo "isolation guard: refusing to run; test and application resolve to the same live PostgreSQL target: $test_target" >&2
  exit 1
fi

echo "isolation guard: PASS"
echo "  test target:        $test_target"
echo "  application target: $application_target"
