package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.PublicationReviewAcknowledgementService;
import com.pompomhills.intelligence.performance.PublicationReviewAcknowledgementService.AcknowledgeRequest;
import com.pompomhills.intelligence.performance.PublicationReviewAcknowledgementService.AcknowledgementView;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST controller for publication review acknowledgement.
 *
 * <p>Allows operators to acknowledge operational guard signals (e.g. PUBLICATION_REVIEW_REQUIRED)
 * so the review is recorded in the append-only ledger. This does not block publication execution.
 */
@RestController
@RequestMapping("/api/v1/performance/publication-review-acknowledgements")
public class PublicationReviewAcknowledgementController {
  private final PublicationReviewAcknowledgementService service;

  public PublicationReviewAcknowledgementController(PublicationReviewAcknowledgementService service) {
    this.service = service;
  }

  /**
   * Acknowledge a guard decision for a platform.
   *
   * @param platform the platform scope (e.g. "facebook")
   * @param request  contains guardDecisionId and optional notes
   * @param actor    the operator identity (passed via query param for simplicity)
   */
  @PostMapping
  public AcknowledgementView acknowledge(
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestBody AcknowledgeRequest request,
      @RequestParam(defaultValue = "anonymous") String actor) {
    return service.acknowledge(platform, request.guardDecisionId(), actor, request.notes());
  }

  /**
   * Check whether a specific guard decision has been acknowledged.
   */
  @GetMapping("/checked/{guardDecisionId}")
  public boolean isAcknowledged(
      @RequestParam(defaultValue = "facebook") String platform,
      @PathVariable UUID guardDecisionId) {
    return service.isAcknowledged(platform, guardDecisionId);
  }

  /**
   * Return the latest acknowledgement for a platform, if any.
   */
  @GetMapping("/latest")
  public AcknowledgementView latest(@RequestParam(defaultValue = "facebook") String platform) {
    return service.latestAcknowledgement(platform);
  }

  /**
   * Return all acknowledgements for a platform.
   */
  @GetMapping
  public List<AcknowledgementView> list(@RequestParam(defaultValue = "facebook") String platform) {
    return service.listAcknowledgements(platform);
  }
}
