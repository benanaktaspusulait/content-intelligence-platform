package com.pompom.creative.api.controller;

import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.time.Instant;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta/operations")
public class MetaOperationsController {
  private final MetaCommentRepository comments;
  private final WebhookEventRepository webhooks;
  private final MetaCommentReplyRepository replies;

  public MetaOperationsController(MetaCommentRepository comments, WebhookEventRepository webhooks, MetaCommentReplyGuard replyGuard) {
    this(comments, webhooks, replyGuard, null);
  }

  @org.springframework.beans.factory.annotation.Autowired
  public MetaOperationsController(MetaCommentRepository comments, WebhookEventRepository webhooks, MetaCommentReplyGuard replyGuard, MetaCommentReplyRepository replies) {
    this.comments = comments;
    this.webhooks = webhooks;
    this.replyGuard = replyGuard;
    this.replies = replies;
  }
  private final MetaCommentReplyGuard replyGuard;

  @GetMapping("/status")
  public Map<String, Object> status() {
    return Map.of(
        "generatedAt", Instant.now(),
        "commentReplyEnabled", replyGuard.isEnabled(),
        "commentCount", comments.count(),
        "pendingWebhookCount", webhooks.findByIsProcessedFalse().size(),
        "processedWebhookCount", webhooks.countByIsProcessedTrue(),
        "replyDraftCount", replies == null ? 0L : replies.countByStatus(com.pompom.creative.domain.MetaCommentReply.Status.DRAFT),
        "replyPendingApprovalCount", replies == null ? 0L : replies.countByStatus(com.pompom.creative.domain.MetaCommentReply.Status.PENDING_APPROVAL),
        "replySentCount", replies == null ? 0L : replies.countByStatus(com.pompom.creative.domain.MetaCommentReply.Status.SENT),
        "replyFailedCount", replies == null ? 0L : replies.countByStatus(com.pompom.creative.domain.MetaCommentReply.Status.FAILED),
        "health", "OK");
  }
}
