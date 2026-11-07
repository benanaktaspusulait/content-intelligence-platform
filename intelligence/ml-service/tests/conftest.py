"""Network-safe, explicit provider test authorization.

Tests may exercise provider adapters, but their environment cannot route traffic
to a real provider. Individual offline-policy tests can override these values.
"""

import pytest


@pytest.fixture(autouse=True)
def explicit_mock_provider_test_policy(monkeypatch):
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", "false")
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", "true")
    # Keep loopback available for local integration tests; force other HTTP(S)
    # traffic through a deliberately unavailable local proxy.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:9")
    monkeypatch.setenv("all_proxy", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1,::1")
    monkeypatch.setenv("no_proxy", "localhost,127.0.0.1,::1")
