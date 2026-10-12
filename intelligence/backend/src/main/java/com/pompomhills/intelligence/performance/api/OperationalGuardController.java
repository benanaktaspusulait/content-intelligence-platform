package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.OperationalGuardService;
import com.pompomhills.intelligence.performance.PublicationReviewAcknowledgementService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for operational guard signals.
 *
 * <p>Returns descriptive distribution and retention health snapshots. When a decision carries
 * PUBLICATION_REVIEW_REQUIRED, the operator can acknowledge it via the publication-review-acknowledgements
 * endpoint so the review is recorded in the append-only ledger.
 */
@RestController
@RequestMapping("/api/v1/performance/operational-guards")
public class OperationalGuardController {
  private final OperationalGuardService service;
  private final PublicationReviewAcknowledgementService acknowledgementService;

  public OperationalGuardController(
      OperationalGuardService service,
      PublicationReviewAcknowledgementService acknowledgementService) {
    this.service = service;
    this.acknowledgementService = acknowledgementService;
  }

  @GetMapping
  public GuardSnapshotWithAcknowledgement latest(
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestParam(defaultValue = "false") boolean evaluate) {
    OperationalGuardService.GuardSnapshot snapshot =
        evaluate ? service.evaluate(platform) : service.latest(platform);
    return withAcknowledgementStatus(snapshot);
  }

  private GuardSnapshotWithAcknowledgement withAcknowledgementStatus(
      OperationalGuardService.GuardSnapshot snapshot) {
    return new GuardSnapshotWithAcknowledgement(
        snapshot.platform(),
        snapshot.enabled(),
        snapshot.decisions().stream()
            .map(decision -> {
              boolean acknowledged = acknowledgementService.isAcknowledged(
                  snapshot.platform(), decision.id());
              return new GuardDecisionWithAcknowledgement(
                  decision.id(),
                  decision.guardType(),
                  decision.platform(),
                  decision.scopeType(),
                  decision.state(),
                  decision.policyVersion(),
                  decision.evidenceCount(),
                  decision.metricValue(),
                  decision.evaluatedAt(),
                  decision.evidence(),
                  acknowledged);
            })
            .toList(),
        snapshot.policyVersion());
  }

  public record GuardSnapshotWithAcknowledgement(
      String platform,
      boolean enabled,
      java.util.List<GuardDecisionWithAcknowledgement> decisions,
      String policyVersion) {}

  public record GuardDecisionWithAcknowledgement(
      UUID id,
      String guardType,
      String platform,
      String scopeType,
      String state,
      String policyVersion,
      int evidenceCount,
      Double metricValue,
      java.time.Instant evaluatedAt,
      String evidence,
      boolean acknowledged) {}
}
