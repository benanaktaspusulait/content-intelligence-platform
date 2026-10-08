-- A successful local repair belongs to one source review; retries cannot create another pass.
CREATE UNIQUE INDEX post_family_single_repair
ON post_family_workflow_events ((payload->>'parentReviewId'))
WHERE kind = 'REPAIR';
