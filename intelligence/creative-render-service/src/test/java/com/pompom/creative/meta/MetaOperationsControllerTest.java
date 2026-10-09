package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.pompom.creative.api.controller.MetaOperationsController;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.util.List;
import org.junit.jupiter.api.Test;

class MetaOperationsControllerTest {
  @Test
  void statusReportsCountsAndGuardStateWithoutExposingContent() {
    var comments = mock(MetaCommentRepository.class);
    var webhooks = mock(WebhookEventRepository.class);
    var guard = mock(MetaCommentReplyGuard.class);
    when(comments.count()).thenReturn(7L);
    when(webhooks.findByIsProcessedFalse()).thenReturn(List.of());
    when(guard.isEnabled()).thenReturn(true);

    var result = new MetaOperationsController(comments, webhooks, guard).status();

    assertThat(result).containsEntry("health", "OK").containsEntry("commentCount", 7L)
        .containsEntry("pendingWebhookCount", 0).containsEntry("commentReplyEnabled", true)
        .containsKey("generatedAt");
    assertThat(result).doesNotContainKey("text").doesNotContainKey("author");
  }
}
