"""Explicit offline/opt-in canonical evidence propagation, no generation interface."""
from copy import deepcopy
from . import beat_grammar, concept_ranking, creative_shape, premise_naturalness
from .canonical_creative_evidence import from_structured
from .short_concept_generation import ranking_input


def evaluate(candidate, structured_input):
    """Acquire once; independent assessors share the same source-bound context."""
    supplied = ranking_input(candidate)
    text = concept_ranking.normalize(supplied)['evaluationText']
    canonical = from_structured(text, structured_input)
    canonical.assert_candidate(candidate)
    result = deepcopy(candidate)
    result['premiseNaturalness'] = premise_naturalness.assess(candidate, canonical_creative_evidence=canonical)
    result['beatGrammar'] = beat_grammar.assess(candidate['structuredBeatPlan'], canonical_creative_evidence=canonical)
    result['storyShapeFingerprint'] = creative_shape.annotate(candidate, canonical_creative_evidence=canonical)
    row = concept_ranking.validate_concept(supplied, canonical_creative_evidence=canonical)
    return result, row, canonical
