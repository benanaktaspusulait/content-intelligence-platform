# POMPOM_GOLDEN_V1 Golden Regression Report

**Calibration release gate:** `PASS`
**Baseline:** RULESET `1.7`

## Summary

| Metric | Value |
|---|---:|
| Assets | 9 |
| Golden assertions | 323 |
| Semantic passed | 104 |
| Semantic failed | 5 |
| Improved from baseline | 0 |
| Unchanged known issues | 54 |
| NEW semantic regressions | 0 |
| Expected policy changes | 0 |
| Unexpected policy regressions | 0 |
| Representation mismatches | 0 |
| Gold review required | 66 |

## Asset Matrix

| Asset | Corpus role | Assertions |
|---|---|---:|
| Luca Ball-Multiplying Crocodile (`ball-crocodile-01`) | WINNER | 36 |
| Luca And The Box Cat (`box-cat-01`) | MIDDLE | 36 |
| Luca And The Island Journal (`island-journal-01`) | NEGATIVE | 35 |
| Kiko And The Lamp That Hates Being Watched (`lamp-01`) | MIDDLE | 36 |
| Mimi And The Snack Box That Keeps Changing (`snack-box-01`) | MIDDLE | 36 |
| Mimi Vs. The Sneaky Door (`sneaky-door-01`) | NEGATIVE | 36 |
| Kiko And The Spot-Stealing Cat (`spot-cat-01`) | NEGATIVE | 36 |
| Luca Sticky Ball (`sticky-ball-01`) | WINNER | 36 |
| Upside-Down Chair (`upside-chair-01`) | WINNER | 36 |

## Full-stack Fingerprint

```json
{
  "assessment_version": "pre-render-assessment-v2",
  "canonical_evidence_version": "canonical-attempt-evidence-v2",
  "engine_input_metadata": {
    "goldenId": "sticky-ball-01",
    "promptHash": "378a39e7d625d5e4e36cd23436b53b0d410b326f02a3c77406853cc51e965e01"
  },
  "frontend_representation_version": "UNKNOWN",
  "git_commit": "ef5d231abd6cc85ad0c394b99517cfa2570b3e0f",
  "gold_label_version": "GOLD_LABELS_V1",
  "golden_set_version": "POMPOM_GOLDEN_V1",
  "parser_version": "prompt-parser-v2",
  "prompt_hash": "378a39e7d625d5e4e36cd23436b53b0d410b326f02a3c77406853cc51e965e01",
  "report_renderer_version": "UNKNOWN",
  "rule_engine_version": "quality-rule-engine-v2",
  "ruleset_version": "1.7",
  "scoring_version": "quality-scorer-v2",
  "semantic_model_version": "gpt-4o",
  "semantic_prompt_version": "UNKNOWN",
  "semantic_provider": "openai",
  "semantic_schema_version": "UNKNOWN"
}
```
