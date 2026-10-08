"""Generator execution port. Local heuristics never claim model-specific proof."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from app.llm.provider import LLMProvider

from .review import valid_span


class ExecutionCritic(Protocol):
    def review(
        self, request: dict[str, Any], evidence: dict[str, Any], generation: dict[str, Any]
    ) -> dict[str, Any]: ...


class LocalExecutionCritic:
    def review(
        self, request: dict[str, Any], evidence: dict[str, Any], generation: dict[str, Any]
    ) -> dict[str, Any]:
        findings = []
        text = request["prompt"]
        patterns = (
            (
                "SIMULTANEOUS_ACTION_COMPETITION",
                r"[^.\n]*\b(?:while|simultaneously)\b[^.\n]*",
                "Hareketler aynı anda yarışabilir.",
                "Öncelikli hareketi belirt; uygunsa diğerini sonra başlat.",
            ),
            (
                "COREFERENCE",
                r"[^.\n]*\b(?:it|they|this|that)\b[^.\n]*",
                "Zamir birden fazla varlığa işaret edebilir.",
                "Zamiri doğrulanmış varlık adıyla değiştir.",
            ),
            (
                "PREMATURE_ENDING",
                r"(?im)^.*\b(?:CUT|END|FADE OUT)\b.*$",
                "Bitiş komutu sonraki olaydan önce gelebilir.",
                "Bitiş komutunu yalnızca son olayın ardından kullan.",
            ),
        )
        for category, pattern, failure, change in patterns:
            for match in list(re.finditer(pattern, text, re.IGNORECASE))[:2]:
                if (
                    category == "COREFERENCE"
                    and len({r.get("character") for r in request.get("references", [])}) < 2
                ):
                    continue
                if category == "PREMATURE_ENDING" and not re.search(r"\d+\s*[-–]\s*\d+", text[match.end() :]):
                    continue
                findings.append(
                    {
                        "sourceSpan": list(match.span()),
                        "sourceQuote": match.group(),
                        "riskCategory": category,
                        "category": category,
                        "plausibleFailure": failure,
                        "evidenceBasis": "GENERAL_HEURISTIC",
                        "confidence": "LOW",
                        "smallestChange": change,
                        "altersCreativeIntent": False,
                    }
                )
        return {
            "stage": "GENERATOR_EXECUTION_REVIEW",
            "status": "REWRITE"
            if findings
            else "PASS"
            if generation["capabilityStatus"] == "SUPPORTED"
            else "UNKNOWN",
            "findings": findings,
            "provider": "LOCAL",
            "model": None,
            "version": "local-execution-critic-v1",
            "visualInspected": False,
            "targetGenerator": generation["selectedGenerator"],
            "limitations": ["Genel yazım sezgileri; seçilen modelin fiili performans kanıtı değildir."],
            "calls": 0,
        }


class ProviderExecutionCritic:
    """One text-only second opinion via the existing provider-neutral port."""

    def __init__(self, provider: LLMProvider, name: str, model: str):
        self.provider, self.name, self.model = provider, name, model

    def review(
        self, request: dict[str, Any], evidence: dict[str, Any], generation: dict[str, Any]
    ) -> dict[str, Any]:
        # Only descriptive reference metadata is forwarded, never private local
        # paths, credentials, audience outcomes or an implicit image attachment.
        context = {
            "prompt": request["prompt"],
            "source": evidence["source"],
            "generation": generation,
            "profile": request.get("contentProfile"),
            "protectedIntent": request.get("protectedIntent"),
            "references": [
                {"sha256": r.get("sha256"), "character": r.get("character")}
                for r in request.get("references", [])
            ],
            "family6": evidence["generalProducibility"]["provenance"]["family6TemporalLoad"],
            "family10": evidence["generalProducibility"],
        }
        try:
            response = self.provider.complete(
                json.dumps(context, ensure_ascii=False),
                system="Text-only generator execution review. No images or video were supplied. "
                "Return JSON status PASS/REWRITE/BLOCK/UNKNOWN, findings array. Each finding needs "
                "sourceSpan [start,end], sourceQuote, riskCategory, plausibleFailure, evidenceBasis "
                "(GENERAL_HEURISTIC, MODEL_DOCUMENTED, OBSERVED_IN_OUR_RENDERS, UNVERIFIED_HYPOTHESIS), "
                "confidence, smallestChange, altersCreativeIntent. "
                "Include no numerical fidelity probability. "
                "Do not claim visual inspection or model-specific evidence "
                "without cited supplied evidence.",
                temperature=0,
            )
            value = json.loads(response)
            if not isinstance(value, dict) or value.get("status") not in {
                "PASS",
                "REWRITE",
                "BLOCK",
                "UNKNOWN",
            }:
                raise ValueError("Invalid critic verdict")
            findings = value.get("findings")
            if not isinstance(findings, list) or (value["status"] in {"REWRITE", "BLOCK"} and not findings):
                raise ValueError("Missing critic findings")
            required = {
                "sourceSpan",
                "sourceQuote",
                "riskCategory",
                "plausibleFailure",
                "evidenceBasis",
                "confidence",
                "smallestChange",
                "altersCreativeIntent",
            }
            for finding in findings:
                if (
                    not isinstance(finding, dict)
                    or not required <= finding.keys()
                    or not valid_span(request["prompt"], finding["sourceSpan"], finding["sourceQuote"])
                ):
                    raise ValueError("Ungrounded critic finding")
                if finding["confidence"] not in {"LOW", "MEDIUM", "HIGH", "UNKNOWN"} or not isinstance(
                    finding["altersCreativeIntent"], bool
                ):
                    raise ValueError("Invalid confidence or intent flag")
                if any(
                    not isinstance(finding[key], str) or not finding[key].strip()
                    for key in ("riskCategory", "plausibleFailure", "smallestChange")
                ):
                    raise ValueError("Incomplete execution finding")
                if finding["evidenceBasis"] not in {"GENERAL_HEURISTIC", "UNVERIFIED_HYPOTHESIS"}:
                    raise ValueError("No model documentation or render observations were supplied")
            if value["status"] == "PASS" and findings:
                raise ValueError("PASS contradicts unresolved findings")
            if value.get("visualInspected") is True:
                raise ValueError("Text-only critic claimed visual inspection")
            if value["status"] == "BLOCK" and all(
                f["evidenceBasis"] in {"GENERAL_HEURISTIC", "UNVERIFIED_HYPOTHESIS"} for f in findings
            ):
                value["status"] = "REWRITE"
            return {
                "status": value["status"],
                "findings": findings,
                "provider": self.name,
                "model": self.model,
                "version": "provider-execution-critic-v1",
                "stage": "GENERATOR_EXECUTION_REVIEW",
                "visualInspected": False,
                "calls": 1,
            }
        except Exception:
            return {
                "status": "UNKNOWN",
                "technicalStatus": "CRITIC_UNAVAILABLE_OR_INVALID",
                "findings": [],
                "provider": self.name,
                "model": self.model,
                "visualInspected": False,
                "calls": 1,
                "stage": "GENERATOR_EXECUTION_REVIEW",
            }
