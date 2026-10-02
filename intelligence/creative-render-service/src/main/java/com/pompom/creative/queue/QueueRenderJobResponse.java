package com.pompom.creative.queue;

import java.util.UUID;

/**
 * Response for {@code POST /api/v1/render-jobs}. {@code replay} is true when this response
 * describes a job that already existed for the given {@code Idempotency-Key} (same key, same
 * canonical payload) rather than one just created.
 */
public record QueueRenderJobResponse(UUID renderJobId, boolean replay) {}
