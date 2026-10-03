"""Canonical family weights shared by the rule engine and enhanced scorer."""

CANONICAL_FAMILY_WEIGHTS: dict[str, float] = {
    "concept_strength": 0.12,
    "hook_strength": 0.12,
    "visual_novelty": 0.14,
    "progression": 0.11,
    "escalation": 0.10,
    "motion_quality": 0.09,
    "readability": 0.08,
    "ai_producibility": 0.10,
    "consistency": 0.07,
    "final_payoff": 0.09,
    "render_risk": 0.08,
    "character_performance": 0.05,
    "generation_executability": 0.09,
}
