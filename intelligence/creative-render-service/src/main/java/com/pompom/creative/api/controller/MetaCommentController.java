package com.pompom.creative.api.controller;

import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.meta.MetaCommentModerationService;
import java.util.UUID;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Human-review API for public Facebook/Instagram comment reply drafts. */
@RestController
@RequestMapping("/api/v1/meta/comments")
@RequiredArgsConstructor
public class MetaCommentController {

  private final MetaCommentModerationService moderation;

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
