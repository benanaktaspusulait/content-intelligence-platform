"""
http_client.py — Minimal HTTP layer for the Meta Graph API.

Standard library only, so the pipeline gains no new mandatory
dependency. Provides:

  * exponential backoff retries for transient failures (429 / 5xx /
    connection resets / timeouts) and no retries for permanent 4xx
  * UTF-8 safe form encoding, so captions survive intact
  * secret scrubbing, so an access token can never reach a log line
"""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from pompom_publisher_common.retry import RETRYABLE_STATUS, RetryPolicy
from pompom_publisher_common.secrets import register_secret, scrub
from .errors import (
    MetaApiError,
    MetaAuthenticationError,
    MetaRateLimitError,
)

log = logging.getLogger("pompom_meta.http")

# Graph API error codes that always mean "fix the token / permissions".
AUTH_ERROR_CODES = {102, 190, 200, 458, 459, 463, 464, 467}

# Graph API throttling codes.
RATE_LIMIT_CODES = {4, 17, 32, 613}

@dataclass
class HttpResponse:
    status: int
    body: bytes
    headers: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> dict:
        if not self.body:
            return {}
        try:
            payload = json.loads(self.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise MetaApiError(
                f"Response was not valid JSON: {exc}",
                status=self.status,
                body=scrub(self.text)[:1000],
            ) from exc
        return payload if isinstance(payload, dict) else {"data": payload}


def encode_form(params: dict) -> bytes:
    """UTF-8 form encoding; None values are dropped."""
    clean = {k: v for k, v in params.items() if v is not None}
    return urllib.parse.urlencode(clean, encoding="utf-8").encode("utf-8")


def _raise_for_graph_error(response: HttpResponse) -> None:
    """Translate a Graph API error payload into a typed exception."""
    body = scrub(response.text)
    error = {}
    try:
        payload = json.loads(response.body.decode("utf-8"))
        if isinstance(payload, dict):
            error = payload.get("error") or {}
    except (ValueError, UnicodeDecodeError):
        error = {}

    message = error.get("message") or f"Graph API request failed ({response.status})"
    code = error.get("code")
    subcode = error.get("error_subcode")
    kwargs = {
        "status": response.status,
        "code": code,
        "subcode": subcode,
        "error_type": error.get("type"),
        "fbtrace_id": error.get("fbtrace_id"),
        "body": body[:2000],
    }

    if response.status in (401, 403) or code in AUTH_ERROR_CODES:
        raise MetaAuthenticationError(scrub(message), **kwargs)
    if response.status == 429 or code in RATE_LIMIT_CODES:
        raise MetaRateLimitError(scrub(message), **kwargs)
    raise MetaApiError(scrub(message), **kwargs)


def request(method: str, url: str, *,
            data: bytes | None = None,
            headers: dict | None = None,
            timeout: float = 120.0,
            retry: RetryPolicy | None = None,
            expect_json: bool = True) -> HttpResponse:
    """Perform an HTTP request with exponential backoff on transient errors.

    Permanent 4xx answers raise immediately; there is no value in retrying
    a bad token or a rejected caption.
    """
    policy = retry or RetryPolicy()
    request_headers = dict(headers or {})
    safe_url = scrub(url)
    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            req = urllib.request.Request(url, data=data, method=method.upper())
            for key, value in request_headers.items():
                req.add_header(key, value)
            with urllib.request.urlopen(req, timeout=timeout) as raw:
                response = HttpResponse(
                    status=raw.status,
                    body=raw.read(),
                    headers=dict(raw.headers.items()),
                )
            if expect_json and response.status >= 400:
                _raise_for_graph_error(response)
            return response

        except urllib.error.HTTPError as exc:
            response = HttpResponse(
                status=exc.code,
                body=exc.read() or b"",
                headers=dict(exc.headers.items()) if exc.headers else {},
            )
            if response.status in RETRYABLE_STATUS and attempt < policy.max_attempts:
                wait = policy.delay_for(attempt)
                log.warning(
                    "%s %s failed with HTTP %s — retry %s/%s in %.0fs",
                    method.upper(), safe_url, response.status,
                    attempt, policy.max_attempts - 1, wait,
                )
                log.debug("Response body: %s", scrub(response.text)[:1000])
                time.sleep(wait)
                last_error = exc
                continue
            _raise_for_graph_error(response)

        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < policy.max_attempts:
                wait = policy.delay_for(attempt)
                log.warning(
                    "%s %s connection error (%s) — retry %s/%s in %.0fs",
                    method.upper(), safe_url, exc,
                    attempt, policy.max_attempts - 1, wait,
                )
                time.sleep(wait)
                continue
            raise MetaApiError(
                f"Connection to Meta failed after {policy.max_attempts} attempts: {exc}"
            ) from exc

    raise MetaApiError(
        f"Request to {safe_url} failed: {last_error}")


def post_form(url: str, params: dict, *, timeout: float = 120.0,
              retry: RetryPolicy | None = None) -> dict:
    """POST an application/x-www-form-urlencoded body and return JSON."""
    response = request(
        "POST", url,
        data=encode_form(params),
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        timeout=timeout,
        retry=retry,
    )
    return response.json()


def get_json(url: str, params: dict | None = None, *, timeout: float = 60.0,
             retry: RetryPolicy | None = None) -> dict:
    """GET a Graph API endpoint and return JSON."""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(clean, encoding='utf-8')}"
    return request("GET", url, timeout=timeout, retry=retry).json()
