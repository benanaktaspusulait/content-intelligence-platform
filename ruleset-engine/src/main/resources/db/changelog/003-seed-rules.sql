--liquibase formatted sql

--changeset pompom:seed-rule-001
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'CONCEPT_001_IMMEDIATE_ANOMALY',
    'Immediate Visual Anomaly',
    'CONCEPT',
    'CRITICAL',
    'CODE',
    'The core concept anomaly must be visible within 0.5-0.8 seconds. This is THE most important concept gate rule.',
    '{"anomalyVisibleBeforeSec": 0.8, "soundOffRequired": true}'::jsonb,
    'STRONGLY_SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-002
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'CONCEPT_002_ONE_DOMINANT_MECHANIC',
    'One Dominant Mechanic',
    'CONCEPT',
    'HIGH',
    'LLM',
    'Video should have ONE clear physical/comedy rule. Multiple mechanics dilute the concept.',
    '{"maxDominantMechanics": 1, "prompt": "Count distinct physical or comedy mechanics in the concept.\n\nConcept: {{conceptText}}\n\nExamples of mechanics:\n- Size change (giant spoon)\n- Gravity reversal (water up)\n- State transfer (dirty/clean)\n- Unstoppable motion (runaway brush)\n\nHow many DIFFERENT core mechanics are described?\n\nScore:\n- 1 mechanic: 100\n- 2 mechanics: 50\n- 3+ mechanics: 0\n\nReturn JSON: {\"mechanicCount\": N, \"mechanics\": [\"list\"], \"score\": 0-100, \"reason\": \"explanation\"}"}'::jsonb,
    'SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-003
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'BEAT_001_ATTEMPT_DIVERSITY',
    'Attempt Diversity',
    'BEAT',
    'HIGH',
    'LLM',
    'SAME PROBLEM + DIFFERENT ATTEMPT + DIFFERENT CONSEQUENCE. Example: POUR → ADD → STIR → DRINK → EMPTY is strong. POUR → POUR → POUR is weak.',
    '{"maxConsecutiveSamePrimaryAction": 1, "maxDominantActionRatio": 0.55, "prompt": "Analyze action diversity in the concept.\n\nConcept: {{conceptText}}\n\nExtract the sequence of PRIMARY ACTIONS (verbs the character takes).\n\nQuestions:\n1. Are there 2+ consecutive identical actions? (BAD)\n2. Does one action dominate >55% of the video? (WEAK)\n3. Are the attempts genuinely different problem-solving strategies?\n\nScore:\n- 90-100: Diverse, distinct solving strategies\n- 70-89: Good variety with minor repetition\n- 50-69: One action dominates or 2 consecutive repeats\n- Below 50: Repetitive structure\n\nReturn JSON: {\"actions\": [\"list\"], \"consecutiveRepeats\": N, \"dominantAction\": \"verb\", \"dominantRatio\": 0.0-1.0, \"score\": 0-100, \"reason\": \"explanation\"}"}'::jsonb,
    'STRONGLY_SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-004
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'BEAT_002_ACTIVITY_NOT_PROGRESSION',
    'Activity Is Not Progression',
    'BEAT',
    'CRITICAL',
    'LLM',
    'Characters moving ≠ story progressing. Example fail: PUSH → MORE PUSH → MORE PEOPLE PUSHING (activity increases, but solving strategy unchanged).',
    '{"prompt": "Evaluate if the concept shows true progression or just increased activity.\n\nConcept: {{conceptText}}\n\nFor each described beat/action:\n1. Does it represent a NEW solving strategy?\n2. Does it produce a NEW type of consequence?\n3. Or is it just \"more of the same with extra characters/force\"?\n\nRed flags:\n- \"they push harder\"\n- \"more friends join\"\n- \"they try again\"\n- WITHOUT a strategy change\n\nScore:\n- 90-100: Clear progression with strategy evolution\n- 70-89: Decent progression with minor repetition\n- 50-69: Some beats are just \"more activity\"\n- Below 50: Mostly increased effort without strategy change\n\nReturn JSON: {\"progressionBeats\": [\"list\"], \"activityBeats\": [\"list\"], \"score\": 0-100, \"reason\": \"explanation\"}"}'::jsonb,
    'SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-005
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'BEAT_003_STORY_DETACHED_GAP',
    'Story Detached Gap',
    'BEAT',
    'CRITICAL',
    'CODE',
    'If the main problem is ongoing, there must NOT be unrelated scenic shots. This is about STORY RELEVANCE absence, not motion absence.',
    '{"maxDetachedDurationSec": 0.5}'::jsonb,
    'SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-006
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'MOTION_001_MEANINGFUL_MOTION',
    'Meaningful Motion',
    'MOTION',
    'HIGH',
    'CODE',
    'CONTINUOUS MEANINGFUL PROGRESSION. We NO LONGER require hands moving EVERY frame. Allowed: 0.7-1.0sec static reaction for educational word reading.',
    '{"staticReactionMaxSec": 0.8, "meaningfulChangePreferredEverySec": 1.5}'::jsonb,
    'SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-007
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'FINAL_001_NEW_CONSEQUENCE',
    'Final New Consequence',
    'FINAL',
    'HIGH',
    'LLM',
    'Final must NOT be just a bigger version of the opening. Preferred: the rule consequence we haven not seen yet.',
    '{"finalMustIntroduceNewConsequence": true, "finalIntensityMustBePeak": true, "prompt": "Evaluate if the final moment introduces a new consequence.\n\nConcept: {{conceptText}}\n\nQuestions:\n1. What is the opening consequence?\n2. What is the final consequence?\n3. Is the final a NEW type of consequence, or just \"more\" of the same?\n4. Is the final the PEAK intensity?\n\nScore:\n- 90-100: Final introduces genuinely new consequence at peak\n- 70-89: Final is strong but somewhat predictable\n- 50-69: Final is just \"bigger\" version of opening\n- Below 50: Final is weak or repetitive\n\nReturn JSON: {\"openingConsequence\": \"description\", \"finalConsequence\": \"description\", \"isNewType\": boolean, \"score\": 0-100, \"reason\": \"explanation\"}"}'::jsonb,
    'SUPPORTED',
    true,
    NOW(),
    NOW()
);

--changeset pompom:seed-rule-008
INSERT INTO rules (id, rule_code, name, category, severity, evaluation_type, description, yaml_definition, evidence_level, active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'LOOPABILITY_001_LOOP_STRUCTURE',
    'Loopability',
    'FINAL',
    'MEDIUM',
    'LLM',
    '15-16 second winner videos had 16-23 second average watch. This means: REPLAY. Loopability is now a separate quality dimension.',
    '{"prompt": "Evaluate loopability potential.\n\nConcept: {{conceptText}}\n\nQuestions:\n1. Does the final state naturally lead back to the opening?\n2. Is there an unfinished action at the end?\n3. Would a viewer be curious to watch again immediately?\n4. Does the concept create a natural cycle?\n\nRed flags for loops:\n- \"Fade out\"\n- \"The end\"\n- \"Problem is solved permanently\"\n- \"Character walks away\"\n\nScore:\n- 90-100: Perfect loop structure, final feeds opening\n- 70-89: Good loop potential with minor gaps\n- 50-69: Weak loop, some continuity\n- Below 50: Designed as one-time narrative\n\nReturn JSON: {\"loopQuality\": \"strong|medium|weak|none\", \"loopMechanism\": \"description\", \"score\": 0-100, \"reason\": \"explanation\"}"}'::jsonb,
    'STRONGLY_SUPPORTED',
    true,
    NOW(),
    NOW()
);
