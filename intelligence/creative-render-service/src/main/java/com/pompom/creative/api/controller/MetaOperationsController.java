package com.pompom.creative.api.controller;

import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.time.Instant;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta/operations")
@RequiredArgsConstructor
public class MetaOperationsController {
  private final MetaCommentRepository comments;
  private final WebhookEventRepository webhooks;
  private final MetaCommentReplyGuard replyGuard;

  @GetMapping("/status")
  public Map<String, Object> status() {
    return Map.of(
        "generatedAt", Instant.now(),
        "commentReplyEnabled", replyGuard.isEnabled(),
        "commentCount", comments.count(),
        "pendingWebhookCount", webhooks.findByIsProcessedFalse().size(),
        "health", "OK");
  }
}
