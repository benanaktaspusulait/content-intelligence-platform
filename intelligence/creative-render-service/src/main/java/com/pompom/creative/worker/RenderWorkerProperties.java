package com.pompom.creative.worker;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration for {@link RenderWorker}. Bound from {@code pompom.render.worker.*}; defaults live
 * in {@code application.yml} (test profiles set {@code enabled: false} so render execution never
 * runs implicitly inside tests that only exercise queueing or persistence).
 *
 * @param enabled whether the scheduled worker tick runs at all
 * @param leaseDuration how long a claimed attempt's lease lasts before it is eligible to be
 *     reclaimed by another worker if this worker crashes or hangs mid-stage
 * @param batchSize maximum number of attempts claimed per tick
 * @param tickInterval how often the worker polls for eligible attempts
 */
@ConfigurationProperties(prefix = "pompom.render.worker")
public record RenderWorkerProperties(
    boolean enabled, Duration leaseDuration, int batchSize, Duration tickInterval) {}
