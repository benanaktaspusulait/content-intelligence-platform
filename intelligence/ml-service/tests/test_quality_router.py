"""Quality router mount verification (Slice A Task 4)."""

from fastapi.testclient import TestClient

from app.main import app


def test_quality_router_health_is_mounted() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/quality/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"UP", "DOWN"}


def test_quality_endpoints_are_reachable_not_404() -> None:
    client = TestClient(app)
    # A mounted but input-invalid POST must be rejected by validation (422),
    # never 404, which would mean the router is not mounted.
    response = client.post("/api/v1/quality/validate", json={})
    assert response.status_code != 404


def test_unknown_ruleset_version_is_not_server_error() -> None:
    client = TestClient(app)
    prompt = "x" * 150
    response = client.post(
        "/api/v1/quality/validate",
        json={"prompt": prompt, "ruleset_version": "does-not-exist-9.9"},
    )
    # An unknown ruleset is a client error (404), not a 500 leaking internals.
    assert response.status_code == 404
