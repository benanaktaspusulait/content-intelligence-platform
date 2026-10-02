#!/bin/bash
# Strict local verification gate for Pompom Creative Intelligence.
#
# Mirrors the blocking CI workflow (.github/workflows/creative-intelligence.yml):
# Java (backend + creative-render-service), ML (ruff + mypy + pytest), the
# repository-level OpenArt wrapper (if its venv is set up), and the Angular
# frontend. No step uses `continue-on-error` or `|| true`; any failure aborts
# the whole gate immediately.
set -euo pipefail

APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$APP/../../../../.." && pwd)"
ML="$APP/ml-service"
WRAPPER="$REPO_ROOT/POMPOM_HILLS_PRODUCTION/00_GLOBAL_RULES/TOOLS/openart_wrapper"

echo "== Java: backend + creative-render-service =="
# spotless:check is scoped to the two code modules (-pl); the aggregator POM
# is packaging-only and has no plugin bound to that goal.
mvn -B -ntp -f "$APP/pom.xml" -pl backend,creative-render-service clean spotless:check verify

echo "== ML: ruff, format, mypy, pytest =="
# Run from within ml-service (not with absolute paths) so mypy/ruff resolve
# pyproject.toml the same way they do when invoked directly during development.
(
  cd "$ML"
  .venv/bin/ruff check app tests
  .venv/bin/ruff format --check app tests
  .venv/bin/mypy app tests
  POMPOM_DATA_ROOT=../data .venv/bin/pytest -q
)

if [ -d "$WRAPPER/.venv" ]; then
  echo "== OpenArt wrapper: ruff, mypy, pytest =="
  "$WRAPPER/.venv/bin/ruff" check "$WRAPPER/openart_wrapper" "$WRAPPER/tests"
  "$WRAPPER/.venv/bin/mypy" "$WRAPPER/openart_wrapper"
  "$WRAPPER/.venv/bin/pytest" -q "$WRAPPER/tests"
else
  echo "== OpenArt wrapper: SKIPPED (no .venv at $WRAPPER/.venv) =="
fi

echo "== Frontend: install, test, build =="
npm --prefix "$APP/frontend" ci
npm --prefix "$APP/frontend" test -- --watch=false
npm --prefix "$APP/frontend" run build -- --configuration production

echo "== verify.sh: all gates passed =="
