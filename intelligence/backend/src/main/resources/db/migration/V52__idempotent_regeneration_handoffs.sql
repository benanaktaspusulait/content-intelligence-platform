CREATE UNIQUE INDEX regeneration_handoff_fingerprint ON post_family_workflow_events((payload->>'handoffFingerprint')) WHERE kind='REGENERATION_HANDOFF' AND payload ? 'handoffFingerprint';
