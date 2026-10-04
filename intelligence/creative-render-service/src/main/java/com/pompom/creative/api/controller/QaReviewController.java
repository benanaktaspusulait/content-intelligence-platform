package com.pompom.creative.api.controller;

import com.pompom.creative.domain.QaHumanReview;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.service.QaHumanReviewService;
import java.util.List;
import java.util.UUID;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import lombok.Data;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read and decision endpoints for the durable human-review gate. */
@RestController
@RequestMapping("/api/v1/qa/reviews")
public class QaReviewController {

  private final QaHumanReviewService reviewService;
  private final String reviewToken;

  public QaReviewController(
      QaHumanReviewService reviewService,
      @Value("${pompom.qa.review-token:}") String reviewToken) {
    this.reviewService = reviewService;
    this.reviewToken = reviewToken;
  }

  @GetMapping("/pending")
  public ResponseEntity<List<RenderQaResult>> pending() {
    return ResponseEntity.ok(reviewService.pendingReviews());
  }

  @GetMapping("/{qaResultId}/history")
  public ResponseEntity<List<QaHumanReview>> history(@PathVariable UUID qaResultId) {
    return ResponseEntity.ok(reviewService.history(qaResultId));
  }

  @PostMapping("/{qaResultId}/decision")
  public ResponseEntity<QaHumanReview> decide(
      @PathVariable UUID qaResultId,
      @RequestHeader(value = "X-QA-Review-Token", required = false) String token,
      @RequestBody DecisionRequest request) {
    try {
      requireReviewToken(token);
      return ResponseEntity.ok(
          reviewService.decide(
              qaResultId,
              QaHumanReview.Decision.valueOf(request.getDecision().toUpperCase()),
              request.getReviewer(),
              request.getNotes()));
    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().build();
    } catch (IllegalStateException e) {
      return ResponseEntity.unprocessableEntity().build();
    }
  }

  private void requireReviewToken(String token) {
    if (reviewToken.isBlank()
        || token == null
        || !MessageDigest.isEqual(
            token.getBytes(StandardCharsets.UTF_8), reviewToken.getBytes(StandardCharsets.UTF_8))) {
      throw new ResponseStatusException(
          HttpStatus.UNAUTHORIZED, "QA review authorization is not configured or invalid");
    }
  }

  @Data
  public static class DecisionRequest {
    private String decision;
    private String reviewer;
    private String notes;
  }
}
