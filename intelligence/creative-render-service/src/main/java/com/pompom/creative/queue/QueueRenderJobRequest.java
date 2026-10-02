package com.pompom.creative.queue;

import com.pompom.creative.domain.RenderJob;
import java.util.Map;

/**
 * Request body for {@code POST /api/v1/render-jobs}.
 *
 * @param requestPromptSha256 optional defense-in-depth check: when a caller already holds the
 *     immutable prompt text (e.g. it just fetched the content/prompt snapshot itself), it may
 *     supply that text's SHA-256 here. {@link ValidationEvidencePolicy} rejects the request if this
 *     does not match the evidence's own prompt hash, catching evidence/content drift at the queue
 *     boundary. Absent (null) is not itself a rejection - the check only runs when present.
 */
public record QueueRenderJobRequest(
    long contentId,
    long promptVersionId,
    long validationRecordId,
    RenderJob.JobType jobType,
    String openartModel,
    Map<String, Object> openartParams,
    String requestPromptSha256) {}
