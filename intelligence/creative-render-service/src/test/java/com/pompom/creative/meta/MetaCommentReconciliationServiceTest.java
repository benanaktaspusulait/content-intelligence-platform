package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.WebhookEventRepository;
import com.pompom.creative.webhook.WebhookService;
import java.util.List;
import org.junit.jupiter.api.Test;

class MetaCommentReconciliationServiceTest {
  @Test
  void replaysOnlyBoundedUnprocessedMetaCommentEvents() {
    WebhookEvent comment = WebhookEvent.builder().platform(PlatformType.FACEBOOK).eventType("meta.public_comment").build();
    WebhookEvent publish = WebhookEvent.builder().platform(PlatformType.FACEBOOK).eventType("published").build();
    WebhookEventRepository repository = mock(WebhookEventRepository.class);
    WebhookService webhookService = mock(WebhookService.class);
    when(repository.findByIsProcessedFalseAndRetryCountLessThan(3)).thenReturn(List.of(comment, publish));
    MetaCommentReconciliationService service = new MetaCommentReconciliationService(repository, webhookService);

    var result = service.reconcile(1);

    assertThat(result.candidates()).isEqualTo(1);
    assertThat(result.replayed()).isEqualTo(1);
    verify(webhookService).processWebhookEvent(comment);
    verify(webhookService, never()).processWebhookEvent(publish);
  }

  @Test
  void clampsNonPositiveLimitToOneAndSkipsOtherPlatforms() {
    WebhookEvent instagram = WebhookEvent.builder().platform(PlatformType.INSTAGRAM).eventType("comment.created").build();
    WebhookEventRepository repository = mock(WebhookEventRepository.class);
    WebhookService webhookService = mock(WebhookService.class);
    when(repository.findByIsProcessedFalseAndRetryCountLessThan(3)).thenReturn(List.of(instagram));
    var result = new MetaCommentReconciliationService(repository, webhookService).reconcile(0);
    assertThat(result.replayed()).isEqualTo(1);
    verify(webhookService).processWebhookEvent(instagram);
  }
}
