"""Pure Family 8 orthogonal quality/evidence/authorization projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

TECHNICAL_REASON_CODES = frozenset({
    "ASSESSMENT_TECHNICAL_FAILURE",
    "PARSER_TIMEOUT",
    "REQUIRED_SERVICE_FAILURE",
})
CREATIVE_REASON_CODES = frozenset({
    "CREATIVE_BLOCKER",
    "CREATIVE_CRITICAL",
})
PENDING_REASON_CODES = frozenset({
    "REQUIRED_EVIDENCE_MISSING",
    "EVIDENCE_PENDING",
    "VISUAL_EVIDENCE_PENDING",
})

AUTHORIZATION_STATUSES = frozenset({
    "AUTHORIZED",
    "BLOCKED_CREATIVE_FAILURE",
    "BLOCKED_TECHNICAL_FAILURE",
    "BLOCKED_PENDING_EVIDENCE",
})


@dataclass(frozen=True)
class AuthorizationReason:
    """One lossless reason contributing to render authorization."""

    code: str
    source: str
    message: str
    references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "source": self.source,
            "message": self.message,
            "references": list(self.references),
        }


def _normalize_reason(value: Mapping[str, Any]) -> AuthorizationReason:
    references = value.get("references") or value.get("evidenceReferences") or ()
    if isinstance(references, str):
        references = (references,)
    return AuthorizationReason(
        code=str(value.get("code") or "UNKNOWN_AUTHORIZATION_REASON"),
        source=str(value.get("source") or "UNKNOWN"),
        message=str(value.get("message") or value.get("reference") or ""),
        references=tuple(str(item) for item in references),
    )


def _reason_category(code: str) -> str | None:
    normalized = code.strip().upper()
    if normalized in TECHNICAL_REASON_CODES or normalized.endswith("_TECHNICAL_FAILURE"):
        return "TECHNICAL"
    if normalized in CREATIVE_REASON_CODES or normalized.startswith("CREATIVE_"):
        return "CREATIVE"
    if normalized in PENDING_REASON_CODES or normalized.endswith("_EVIDENCE"):
        return "PENDING"
    return None


def _primary_authorization_status(reasons: tuple[AuthorizationReason, ...]) -> str:
    categories = {_reason_category(reason.code) for reason in reasons}
    if "TECHNICAL" in categories:
        return "BLOCKED_TECHNICAL_FAILURE"
    if "CREATIVE" in categories:
        return "BLOCKED_CREATIVE_FAILURE"
    if "PENDING" in categories:
        return "BLOCKED_PENDING_EVIDENCE"
    if reasons:
        # Unknown blocking reasons fail closed without pretending they are
        # creative failures or user-resolvable evidence gaps.
        return "BLOCKED_TECHNICAL_FAILURE"
    return "AUTHORIZED"


def render_admission_allowed(render_authorization: Mapping[str, Any] | None) -> bool:
    """Allow admission only for the exact canonical AUTHORIZED status."""

    return bool(
        isinstance(render_authorization, Mapping)
        and render_authorization.get("status") == "AUTHORIZED"
    )


def project_family8(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Project three orthogonal Family 8 facts without changing policy."""

    creative_input = dict(facts.get("creativeQuality") or {})
    evidence_input = dict(facts.get("evidenceCompleteness") or {})
    legacy_input = dict(facts.get("legacy") or {})
    reasons = tuple(
        _normalize_reason(item)
        for item in (facts.get("authorizationReasons") or [])
        if isinstance(item, Mapping)
    )
    status = _primary_authorization_status(reasons)
    return {
        "creativeQuality": {
            "creativeScore": creative_input.get("creativeScore"),
            "creativeGrade": creative_input.get("creativeGrade"),
            "familyScores": dict(creative_input.get("familyScores") or {}),
        },
        "evidenceCompleteness": {
            "status": evidence_input.get("status"),
            "evaluationCoverage": evidence_input.get("evaluationCoverage"),
            "aggregation": dict(evidence_input.get("aggregation") or {}),
        },
        "renderAuthorization": {
            "status": status,
            "reasons": [reason.to_dict() for reason in reasons],
        },
        "legacy": {
            "readiness": legacy_input.get("readiness"),
        },
    }
