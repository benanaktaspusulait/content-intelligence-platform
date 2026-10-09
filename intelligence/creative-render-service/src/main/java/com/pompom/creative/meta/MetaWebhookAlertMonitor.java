package com.pompom.creative.meta;

import com.pompom.creative.repository.WebhookEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Emits privacy-safe operational warnings when Meta webhook backlog needs attention. */
@Component
@RequiredArgsConstructor
@Slf4j
public class MetaWebhookAlertMonitor {
  private final WebhookEventRepository webhooks;

  @Value("${pompom.meta.webhook-alert-threshold:50}")
  private int threshold;

  @Scheduled(fixedDelayString = "${pompom.meta.webhook-alert-interval-ms:60000}")
  public void checkBacklog() {
    int pending = webhooks.findByIsProcessedFalse().size();
    if (pending >= Math.max(1, threshold)) {
      log.warn("Meta webhook backlog threshold exceeded: pendingCount={}, threshold={}", pending, threshold);
    }
  }
}
