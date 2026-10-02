from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import AnalysisArtifacts, AnalysisResult


def artifacts(data_dir: Path, video_id: str) -> AnalysisArtifacts:
    root = data_dir / "output" / "analyses" / video_id
    return AnalysisArtifacts(
        root=root,
        frames_dir=root / "frames",
        storyboard=root / "storyboard.jpg",
        analysis_json=root / "analysis.json",
        report_md=root / "report.md",
        timeline_json=root / "timeline.json",
        fix_json=root / "fix_plan.json",
        fix_md=root / "fix_plan.md",
    )


def write_reports(result: AnalysisResult, paths: AnalysisArtifacts) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.analysis_json.write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=False) + "\n")
    paths.timeline_json.write_text(json.dumps([asdict(item) for item in result.timeline], indent=2, ensure_ascii=False) + "\n")
    paths.fix_json.write_text(json.dumps([asdict(item) for item in result.fix_plan], indent=2, ensure_ascii=False) + "\n")
    paths.fix_md.write_text(_fix_markdown(result))
    paths.report_md.write_text(_report_markdown(result))


def _stamp(start: float, end: float) -> str:
    return f"{start:05.2f}-{end:05.2f}s"


def _report_markdown(result: AnalysisResult) -> str:
    issues = "\n".join(
        f"- **{_stamp(item.start, item.end)} {item.code} ({item.severity})**: {item.evidence} "
        f"Consequence: {item.consequence} Change: {item.proposed_change}"
        for item in result.issues
    ) or "- No deterministic structural issue was found. Human semantic review is still required."
    timeline = "\n".join(f"- `{_stamp(item.start, item.end)}` **{item.kind}** - {item.detail}" for item in result.timeline) or "- No events."
    audio = "\n".join(f"- `{_stamp(item.start, item.end)}` {item.detail}" for item in result.audio_findings) or "- No notable local audio finding."
    scores = "\n".join(f"- {key.replace('_', ' ').title()}: **{value}/10**" for key, value in result.scores.items())
    return f"""# Creative Analysis - {result.metadata.filename}

## 1. Classification

**{result.classification}** - {result.classification_reason}

## 2. Creative Structure Match

**{result.creative_structure_match}/100** (confidence {result.confidence:.0%})

This is a creative-structure match, not a view or success prediction.

## 3. Diagnosis

{result.diagnosis}

## 4. Scores

{scores}

## 5. Strengths

{chr(10).join('- ' + item for item in result.strengths)}

## 6. Weaknesses and Exact Fixes

{issues}

## 7. Timeline

{timeline}

## 8. Character Goal and Physical Rule

- Goal: {result.semantic_notes.get('goal', 'Not available')}
- Rule: {result.semantic_notes.get('physical_rule', 'Not available')}
- Provider: `{result.provider}` / `{result.model}`

## 9. Physical Actions

{chr(10).join(f'- `{_stamp(item.start, item.end)}` {item.detail}' for item in result.physical_actions) or '- No reliable action peaks detected.'}

## 10. Fake Resolution

{result.semantic_notes.get('fake_resolution', 'Not semantically verified.')}

## 11. Final Twist and Loop

- Final twist score: {result.scores['final_twist']}/10
- Loopability score: {result.scores['loopability']}/10

## 12. Continuity / Generation Defects

{result.semantic_notes.get('continuity', 'Not semantically verified.')}

## 13. Text / CTA

{result.semantic_notes.get('text', 'Not semantically verified.')}

## 14. Audio

{audio}

## 15. Publishing Recommendation

{_recommendation(result.classification)}

## 16. Evidence Frames

See `storyboard.jpg` and the timestamped files under `frames/`.
"""


def _recommendation(classification: str) -> str:
    return {
        "BAD": "Do not use a prime slot. Human-review whether the concept needs regeneration rather than editing.",
        "AVERAGE/FIXABLE": "Do not publish untouched. Review and, where safe, render the proposed non-destructive candidate.",
        "GOOD": "Suitable for a normal slot after human continuity and text review.",
        "WINNER CANDIDATE": "Preserve the original and use a controlled prime-slot test; no performance outcome is guaranteed.",
    }[classification]


def _fix_markdown(result: AnalysisResult) -> str:
    if not result.fix_plan:
        return "# Fix Plan\n\nNo safe deterministic edit was proposed. Human creative review is required.\n"
    lines = ["# Fix Plan", "", "All operations use existing footage and never overwrite the source.", ""]
    for index, item in enumerate(result.fix_plan, 1):
        bounds = ", ".join(f"{key}={value:.3f}s" for key, value in (("start", item.start), ("end", item.end)) if value is not None)
        lines.append(f"{index}. **{item.operation}** {bounds} - {item.reason}")
    return "\n".join(lines) + "\n"

