package com.pompom.creative.worker;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Periodically claims eligible {@code RenderAttempt} rows and dispatches each to {@link
 * RenderAttemptOrchestrator#processAttempt} for exactly one stage of execution.
 *
 * <p>Multiple instances of this worker (e.g. several application processes) can run concurrently
 * and safely: {@link RenderAttemptClaimRepository#claimEligibleAttempts} is atomic, so no two ticks
 * - whether on this instance or another - ever receive the same attempt ID. A worker that crashes
 * mid-attempt simply leaves its lease to expire; the next tick (on any instance) reclaims it.
 */
@Component
@Slf4j
public class RenderWorker {

  private final RenderAttemptClaimRepository claimRepository;
  private final RenderAttemptOrchestrator orchestrator;
  private final RenderWorkerProperties properties;
  private final String leaseOwner = "render-worker-" + UUID.randomUUID();

  public RenderWorker(
      RenderAttemptClaimRepository claimRepository,
      RenderAttemptOrchestrator orchestrator,
      RenderWorkerProperties properties) {
    this.claimRepository = claimRepository;
    this.orchestrator = orchestrator;
    this.properties = properties;
  }

  /**
   * Claim up to {@code batchSize} eligible attempts under this worker's lease owner and process
   * each one. A failure processing one claimed attempt (including losing the lease to another
   * worker between claim and dispatch) is logged and does not prevent the rest of the batch from
   * being processed.
   */
  @Scheduled(fixedDelayString = "${pompom.render.worker.tick-interval:5s}")
  public void tick() {
    if (!properties.enabled()) {
      return;
    }

    Instant now = Instant.now();
    Instant leaseExpiresAt = now.plus(properties.leaseDuration());

    List<UUID> claimed =
        claimRepository.claimEligibleAttempts(
            leaseOwner, now, leaseExpiresAt, properties.batchSize());

    if (claimed.isEmpty()) {
      return;
    }

    log.info("Worker {} claimed {} attempt(s)", leaseOwner, claimed.size());

    for (UUID attemptId : claimed) {
      try {
        orchestrator.processAttempt(attemptId, leaseOwner);
      } catch (Exception e) {
        log.error(
            "Worker {} failed to process attempt {}: {}", leaseOwner, attemptId, e.getMessage(), e);
      }
    }
  }
}
