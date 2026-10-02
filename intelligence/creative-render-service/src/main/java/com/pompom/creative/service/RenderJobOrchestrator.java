package com.pompom.creative.service;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.websocket.WebSocketEventPublisher;
import com.pompom.creative.websocket.dto.RenderProgressEvent;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Queues render jobs. Execution of a queued job's stages (provider submission, polling, download,
 * QA, and rerender/abandon decisions) is handled per-attempt by {@code RenderAttemptOrchestrator}
 * in the {@code worker} package - see that class for why: a worker claims one durable {@code
 * RenderAttempt} row at a time and advances it exactly one stage per call, which replaced this
 * class's previous single-long-transaction {@code executeRenderJob} with its recursive rerender.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class RenderJobOrchestrator {

  private final RenderJobRepository renderJobRepo;
  private final RenderAttemptRepository renderAttemptRepo;
  private final IntelligenceContentClient intelligenceContentClient;
  private final CreditTrackingService creditTrackingService;
  private final BudgetAlertService budgetAlertService;
  private final WebSocketEventPublisher webSocketPublisher;

  // Self reference so the public (non-transactional) queue method can invoke the transactional
  // persistence method through the Spring proxy. Injected lazily to avoid a construction cycle;
  // left null in plain unit tests, where persistQueuedJob is called directly on `this`.
  @Autowired @Lazy private RenderJobOrchestrator self;

  /**
   * Queue a new render job for a content and prompt version.
   *
   * <p>Intentionally NOT {@code @Transactional}: the remote intelligence fetch (a potentially slow
   * network call) runs before any database transaction is opened, so it never holds a pooled DB
   * connection. Only the subsequent {@link #persistQueuedJob} runs inside a transaction.
   */
  public UUID queueRenderJob(Long contentId, Long promptVersionId, RenderJob.JobType jobType) {
    log.info(
        "Queueing render job: contentId={}, promptVersionId={}, jobType={}",
        contentId,
        promptVersionId,
        jobType);

    // Check budget and alerts before queueing
    budgetAlertService.checkBudgetBeforeRender();

    if (!creditTrackingService.canAffordRender(jobType)) {
      throw new IllegalStateException(
          "Insufficient budget to queue render job. Remaining credits: "
              + creditTrackingService.getRemainingCredits());
    }

    // Fetch an immutable content/prompt snapshot across the service boundary, BEFORE opening a
    // DB transaction. The render service never touches intelligence tables directly.
    ContentPromptSnapshot snapshot = intelligenceContentClient.fetch(contentId, promptVersionId);

    // Get estimated cost
    BigDecimal estimatedCredits = creditTrackingService.getEstimatedCost(jobType);

    // Persist inside a transaction (via the proxy so @Transactional applies in production).
    RenderJobOrchestrator tx = self != null ? self : this;
    return tx.persistQueuedJob(snapshot, jobType, estimatedCredits);
  }

  /**
   * Persist a queued render job from an already-fetched snapshot. Runs in its own transaction; the
   * slow remote fetch has already completed by the time this method is entered.
   */
  @Transactional
  public UUID persistQueuedJob(
      ContentPromptSnapshot snapshot, RenderJob.JobType jobType, BigDecimal estimatedCredits) {
    // Create render job with scalar ownership + immutable prompt snapshot
    RenderJob job =
        RenderJob.builder()
            .contentId(snapshot.contentId())
            .promptVersionId(snapshot.promptVersionId())
            .contentTitleSnapshot(snapshot.contentTitle())
            .promptVersionNumberSnapshot(snapshot.promptVersionNumber())
            .promptSha256(snapshot.promptSha256())
            .promptTextSnapshot(snapshot.promptText())
            .jobType(jobType)
            .openartModel("mock_model") // Will be configurable in future
            .status(RenderJob.RenderJobStatus.QUEUED)
            .attemptNumber(1)
            .maxAttempts(3)
            .creditsEstimated(estimatedCredits)
            .queuedAt(Instant.now())
            .build();

    job = renderJobRepo.save(job);
    log.info(
        "Created render job: id={}, status={}, estimatedCredits={}",
        job.getId(),
        job.getStatus(),
        estimatedCredits);

    // Create the first durable attempt row so a worker has something to claim; the job itself
    // carries no execution state beyond this point - RenderAttemptOrchestrator owns it.
    renderAttemptRepo.save(RenderAttempt.firstAttemptFor(job.getId()));

    // Publish WebSocket event
    publishProgressEvent(
        job,
        RenderProgressEvent.EventType.JOB_STARTED,
        "Job queued",
        0,
        estimatedCredits.intValue());

    return job.getId();
  }

  /** Publish WebSocket progress event. */
  private void publishProgressEvent(
      RenderJob job,
      RenderProgressEvent.EventType eventType,
      String currentStep,
      Integer progressPercent,
      Integer creditsUsed) {
    try {
      RenderProgressEvent event =
          RenderProgressEvent.builder()
              .type(eventType)
              .jobId(job.getId())
              .status(job.getStatus().name())
              .progressPercent(progressPercent)
              .currentStep(currentStep)
              .creditsUsed(creditsUsed)
              .errorMessage(job.getErrorMessage())
              .build();

      webSocketPublisher.publishRenderProgress(event);
    } catch (Exception e) {
      // Don't fail the job if WebSocket publish fails
      log.warn("Failed to publish WebSocket event for job {}: {}", job.getId(), e.getMessage());
    }
  }
}
