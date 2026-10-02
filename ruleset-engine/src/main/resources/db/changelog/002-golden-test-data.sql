--liquibase formatted sql

--changeset pompom:golden-positive-001
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_min_score, expected_failing_rules, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_POS_001_GIANT_SPOON',
    'POSITIVE',
    'Giant spoon that gets bigger with every pour. Kiko pours water, spoon grows. Adds ingredient, spoon grows more. Stirs, spoon is now huge. Tries to drink, spoon too big for mouth. Final: spoon fills entire kitchen.',
    'GROWTH',
    true,
    85.0,
    NULL,
    'THE canonical winner. If this fails, something is very wrong.',
    NOW()
);

--changeset pompom:golden-positive-002
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_min_score, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_POS_002_KIRLI_MIMI',
    'POSITIVE',
    'Mimi has dirty hands. Water makes them dirtier. Soap cleans them. Opening: Mimi hands are dirty. Beat 1: Tries to wash with water - hands get MORE dirty. Beat 2: Looks at hands, confused. Beat 3: Uses soap - hands become clean. Beat 4: Touches dirty surface - hands dirty again. Final: Major scrub with soap, water splashing.',
    'GROWTH',
    true,
    90.0,
    'Proven winner with 31K views. WATER → DIRTY, SOAP → CLEAN',
    NOW()
);

--changeset pompom:golden-positive-003
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_min_score, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_POS_003_RUNAWAY_TOOTHBRUSH',
    'POSITIVE',
    'Toothbrush that won''t stop moving once started. Opening: Arda activates electric toothbrush. Beat 1: Brush starts moving in hand. Beat 2: Brush pulls away, moving on its own. Beat 3: Arda chases it around bathroom. Beat 4: Brush zooms under sink, over counter. Final: Brush spinning wildly in mid-air, Arda lunging.',
    'GROWTH',
    true,
    85.0,
    'One mechanic: unstoppable motion. 28K views.',
    NOW()
);

--changeset pompom:golden-negative-001
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_max_score, expected_failing_rules, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_NEG_001_DOOR_PUSH',
    'NEGATIVE',
    'Characters try to open a stuck door. Kiko pushes door, doesn''t open. Kiko pushes harder. Mimi joins, both push. Arda joins, all three push. Cut to scenic landscape for 2 seconds. Back to door, everyone pushing. Door finally opens.',
    'GROWTH',
    false,
    50.0,
    '["CONCEPT_001_IMMEDIATE_ANOMALY", "BEAT_002_ACTIVITY_NOT_PROGRESSION", "BEAT_003_STORY_DETACHED_GAP"]'::jsonb,
    'Canonical failure: no immediate anomaly, activity not progression, detached scenic insert.',
    NOW()
);

--changeset pompom:golden-negative-002
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_max_score, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_NEG_002_BACKPACK',
    'NEGATIVE',
    'Backpack gets heavier as items are added. Sofia puts book in backpack. Backpack feels heavier. Adds pencil case, heavier still. Adds lunch box, very heavy now. Struggles to lift backpack. Backpack too heavy to carry.',
    'GROWTH',
    false,
    40.0,
    'Weight is not visually immediate. Repetitive action: add → add → add.',
    NOW()
);

--changeset pompom:golden-negative-003
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_max_score, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_NEG_003_CARROT',
    'NEGATIVE',
    'Carrot slowly grows bigger while character watches. Tiny carrot on plate. Carrot grows slightly. Character looks surprised. Carrot grows more. Character reaches for it. Carrot is now medium-sized. Carrot fills plate.',
    'GROWTH',
    false,
    50.0,
    'Character is passive. No attempt diversity. Gradual change without distinct beats.',
    NOW()
);
