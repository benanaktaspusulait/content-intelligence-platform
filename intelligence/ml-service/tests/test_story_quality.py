from app.workflow.story_quality import analyse_story_candidates


def test_rephrasings_are_near_duplicates() -> None:
    result = analyse_story_candidates([
        'Mimi pulls sticky notes away, then becomes covered in notes.',
        'Mimi quickly yanks the sticky notes off, then ends covered in notes.',
        'Mimi removes the notes and finally is covered by sticky notes.',
    ], {'profile': 'ABSURD_PHYSICS'})
    assert result['classification'] == 'NEAR_DUPLICATE'
    assert result['variationClass'] == 'PARAPHRASE_OR_NEAR_DUPLICATE'
    assert result['method'] == 'story-structure-v1'


def test_distinct_progressions_are_distinct() -> None:
    result = analyse_story_candidates([
        'Mimi opens the cabinet and the notes fly after her. She hides beside it and discovers a map.',
        'Mimi shakes the cabinet to save a toy, revealing the notes were attached to a hidden drawer.',
        'Mimi follows one note through the room and learns it points to a missing friend.',
    ], {'profile': 'CURIOSITY_ADVENTURE'})
    assert result['classification'] in {'DISTINCT', 'PARTIALLY_DISTINCT'}
    assert result['candidates'][0]['preflight']['opening'] == 'SUPPORTED'


def test_multiplication_and_occlusion_are_contextual_findings() -> None:
    result = analyse_story_candidates([
        'Mimi hides behind the cabinet while sticky notes multiply and cover her.',
    ], {'profile': 'ABSURD_PHYSICS'})
    preflight = result['candidates'][0]['preflight']
    assert any('second rule' in item for item in preflight['concerns'])
    assert any('contextual staging risk' in item for item in preflight['productionRisks'])
