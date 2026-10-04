package com.pompom.creative.worker;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class PublicationWorker {

  private final PublicationAttemptClaimRepository claimRepository;
  private final PublicationAttemptOrchestrator orchestrator;
  private final String leaseOwner = "publication-worker-" + UUID.randomUUID();

  @Value("${pompom.publication.worker.enabled:true}")
  private boolean enabled;

  @Value("${pompom.publication.worker.batch-size:5}")
  private int batchSize;

  @Value("${pompom.publication.worker.lease-duration:PT15M}")
  private Duration leaseDuration;

  public PublicationWorker(
      PublicationAttemptClaimRepository claimRepository,
      PublicationAttemptOrchestrator orchestrator) {
    this.claimRepository = claimRepository;
    this.orchestrator = orchestrator;
  }

  @Scheduled(fixedDelayString = "${pompom.publication.worker.tick-interval:5s}")
  public void tick() {
    if (!enabled) {
      return;
    }
    orchestrator.reconcileExpiredSubmissions();
    Instant now = Instant.now();
    for (UUID attemptId :
        claimRepository.claimQueuedAttempts(leaseOwner, now, now.plus(leaseDuration), batchSize)) {
      try {
        orchestrator.processAttempt(attemptId, leaseOwner);
      } catch (Exception error) {
        log.error("Publication attempt {} failed to execute", attemptId, error);
      }
    }
  }
}
