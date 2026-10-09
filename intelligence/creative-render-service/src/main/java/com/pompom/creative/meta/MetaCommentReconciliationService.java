package com.pompom.creative.meta;

import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.repository.WebhookEventRepository;
import com.pompom.creative.webhook.WebhookService;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Replays bounded failed Meta comment webhook deliveries to close event gaps. */
@Service
@RequiredArgsConstructor
public class MetaCommentReconciliationService {
  private final WebhookEventRepository webhookEvents;
  private final WebhookService webhookService;

  @Transactional
  public ReconciliationResult reconcile(int limit) {
    int bounded = Math.max(1, Math.min(100, limit));
    List<WebhookEvent> candidates =
        webhookEvents.findByIsProcessedFalseAndRetryCountLessThan(3).stream()
            .filter(this::isMetaCommentEvent)
            .limit(bounded)
            .toList();
    int processed = 0;
    for (WebhookEvent event : candidates) {
      webhookService.processWebhookEvent(event);
      processed++;
    }
    return new ReconciliationResult(candidates.size(), processed);
  }

  private boolean isMetaCommentEvent(WebhookEvent event) {
    return event.getPlatform() != null
        && (event.getPlatform().name().equals("FACEBOOK")
            || event.getPlatform().name().equals("INSTAGRAM"))
        && event.getEventType() != null
        && event.getEventType().toLowerCase().contains("comment");
  }

  public record ReconciliationResult(int candidates, int replayed) {}
}
