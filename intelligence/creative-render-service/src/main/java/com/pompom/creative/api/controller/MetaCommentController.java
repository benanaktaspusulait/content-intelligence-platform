package com.pompom.creative.api.controller;

import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.meta.MetaCommentModerationService;
import com.pompom.creative.meta.MetaCommentReplyDeliveryService;
import com.pompom.creative.meta.MetaCommentReconciliationService;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.oauth.MetaCommentReplyDisabledException;
import java.util.UUID;
import java.util.List;
import lombok.Data;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Human-review API for public Facebook/Instagram comment reply drafts. */
@RestController
@RequestMapping("/api/v1/meta/comments")
public class MetaCommentController {

  private final MetaCommentModerationService moderation;
  private final MetaCommentReplyDeliveryService delivery;
  private final MetaCommentReconciliationService reconciliation;
  private final MetaCommentRepository comments;

  /** Compatibility constructor for isolated controller tests. */
  @Autowired
  public MetaCommentController(
      MetaCommentModerationService moderation, MetaCommentReplyDeliveryService delivery) {
    this(moderation, delivery, null, null);
  }

  public MetaCommentController(
      MetaCommentModerationService moderation,
      MetaCommentReplyDeliveryService delivery,
      MetaCommentReconciliationService reconciliation,
      MetaCommentRepository comments) {
    this.moderation = moderation;
    this.delivery = delivery;
    this.reconciliation = reconciliation;
    this.comments = comments;
  }

  @GetMapping
  public ResponseEntity<List<com.pompom.creative.domain.MetaComment>> list() {
    return ResponseEntity.ok(comments == null ? List.of() : comments.findTop100ByOrderByCreatedAtDesc());
  }

  @PostMapping("/reconcile")
  public ResponseEntity<MetaCommentReconciliationService.ReconciliationResult> reconcile(
      @RequestParam(defaultValue = "50") int limit) {
    return ResponseEntity.ok(reconciliation.reconcile(limit));
  }

  @PostMapping("/{commentId}/replies/draft")
  public ResponseEntity<MetaCommentReply> createDraft(
      @PathVariable UUID commentId, @RequestBody DraftRequest request) {
    return ResponseEntity.ok(
        moderation.createDraft(commentId, request.getDraftText(), request.getIdempotencyKey()));
  }

  @PostMapping("/replies/{replyId}/submit")
  public ResponseEntity<MetaCommentReply> submit(@PathVariable UUID replyId) {
    return ResponseEntity.ok(moderation.submitForApproval(replyId));
  }

  @PostMapping("/replies/{replyId}/approve")
  public ResponseEntity<MetaCommentReply> approve(
      @PathVariable UUID replyId, @RequestBody ReviewRequest request) {
    return ResponseEntity.ok(moderation.approve(replyId, request.getReviewer()));
  }

  @PostMapping("/replies/{replyId}/reject")
  public ResponseEntity<MetaCommentReply> reject(
      @PathVariable UUID replyId, @RequestBody ReviewRequest request) {
    return ResponseEntity.ok(
        moderation.reject(replyId, request.getReviewer(), request.getReason()));
  }

  @PostMapping("/replies/{replyId}/send")
  public ResponseEntity<MetaCommentReply> send(@PathVariable UUID replyId) {
    try {
      return ResponseEntity.ok(delivery.send(replyId));
    } catch (MetaCommentReplyDisabledException e) {
      return ResponseEntity.status(403).build();
    } catch (IllegalStateException e) {
      return ResponseEntity.badRequest().build();
    } catch (IllegalArgumentException e) {
      return ResponseEntity.notFound().build();
    }
  }

  @Data
  public static class DraftRequest {
    private String draftText;
    private String idempotencyKey;
  }

  @Data
  public static class ReviewRequest {
    private String reviewer;
    private String reason;
  }
}
