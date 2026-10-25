-- Immutable identities use existing append-only workflow events.
CREATE UNIQUE INDEX idea_request_identity ON post_family_workflow_events(binding_sha256) WHERE kind='IDEA_REQUEST';
CREATE UNIQUE INDEX idea_receipt_identity ON post_family_workflow_events(binding_sha256) WHERE kind='IDEA_RECEIPT';
CREATE UNIQUE INDEX idea_candidate_identity ON post_family_workflow_events(binding_sha256) WHERE kind='IDEA_CANDIDATE';
