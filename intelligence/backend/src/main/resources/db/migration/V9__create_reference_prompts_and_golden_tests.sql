-- V9: Reference Prompts table and golden test case seeds

CREATE TABLE reference_prompts (
    id BIGSERIAL PRIMARY KEY,
    character_name VARCHAR(100) NOT NULL,
    scenario_type VARCHAR(100) NOT NULL,
    reference_text TEXT NOT NULL,
    expected_score DECIMAL(5,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(character_name, scenario_type)
);

CREATE INDEX idx_reference_prompts_character_name ON reference_prompts(character_name);
CREATE INDEX idx_reference_prompts_expected_score ON reference_prompts(expected_score);

COMMENT ON TABLE reference_prompts IS 'Golden reference prompts for testing validation engine';

-- Seed 4 golden test cases
INSERT INTO reference_prompts (character_name, scenario_type, reference_text, expected_score, notes) VALUES
(
    'Kiko',
    'static_state_failure',
    E'Beat 1: Kiko tries to slide on smooth ice\nBeat 2: Kiko touches rough tree bark\nBeat 3: Kiko slides on smooth ice again\nBeat 4: Kiko touches rough bark again\nBeat 5: Kiko on smooth ice\nBeat 6: Kiko on rough bark\nBeat 7: Kiko discovers smooth ice is slippery\nBeat 8: Kiko learns rough bark has texture',
    42.00,
    'BLOCKED - Static state cycle: slippery/rough alternates without progression. Should score <50.'
),
(
    'Opa',
    'repetition_failure',
    E'Beat 1: Opa examines old photograph\nBeat 2: Opa finds new camera\nBeat 3: Opa looks at old photograph again\nBeat 4: Opa compares with new camera\nBeat 5: Opa holds old photograph\nBeat 6: Opa tests new camera\nBeat 7: Opa thinks about old memories\nBeat 8: Opa captures new moment',
    38.00,
    'BLOCKED - Old/new repetition without emotional progression. Should score <50.'
),
(
    'Arda',
    'cycle_failure',
    E'Beat 1: Arda examines sharp pencil\nBeat 2: Arda tries blunt crayon\nBeat 3: Arda returns to sharp pencil\nBeat 4: Arda tests blunt crayon again\nBeat 5: Arda picks sharp pencil\nBeat 6: Arda drops blunt crayon\nBeat 7: Arda chooses sharp pencil for drawing\nBeat 8: Arda realizes tools have different purposes',
    45.00,
    'BLOCKED - Sharp/blunt cycle without meaningful discovery. Should score <50.'
),
(
    'Mimi',
    'progression_success',
    E'Beat 1: Mimi sees muddy puddle\nBeat 2: Mimi steps carefully around it\nBeat 3: Mimi notices friend struggling with dirty hands\nBeat 4: Mimi shares clean cloth\nBeat 5: Mimi helps friend clean up\nBeat 6: Mimi and friend find clean water\nBeat 7: Both wash hands together\nBeat 8: Mimi smiles - helping feels good',
    94.00,
    'RENDER_READY - Clear progression: awareness → avoidance → empathy → helping → sharing → connection. Should score >92.'
);
