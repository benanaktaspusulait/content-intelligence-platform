package com.pompom.creative.meta;

import static org.mockito.Mockito.*;
import com.pompom.creative.repository.WebhookEventRepository;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

class MetaWebhookAlertMonitorTest {
  @Test
  void checksPendingWebhookBacklogWithoutLoggingPayloads() {
    WebhookEventRepository repository = mock(WebhookEventRepository.class);
    when(repository.findByIsProcessedFalse()).thenReturn(java.util.List.of());
    MetaWebhookAlertMonitor monitor = new MetaWebhookAlertMonitor(repository);
    ReflectionTestUtils.setField(monitor, "threshold", 1);
    monitor.checkBacklog();
    verify(repository).findByIsProcessedFalse();
  }
}
