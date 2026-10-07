package com.pompom.creative.webhook;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class WebhookCommentRoutingTest {

  private final WebhookEventRepository eventRepository = mock(WebhookEventRepository.class);
  private final PublicationJobRepository publicationJobRepository =
      mock(PublicationJobRepository.class);
  private WebhookService service;

  @BeforeEach
  void setUp() {
    service = new WebhookService(eventRepository, publicationJobRepository, new ObjectMapper());
    when(eventRepository.findByDeliveryKey(any())).thenReturn(Optional.empty());
    when(eventRepository.save(any(WebhookEvent.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    when(publicationJobRepository.findAll()).thenReturn(java.util.List.of());
  }

  @Test
  void persistsFacebookCommentWebhookWithoutPublicationEventParsing() {
    String payload =
        """
        {
          "object": "page",
          "entry": [{
            "id": "page-1",
            "changes": [{
              "field": "feed",
              "value": {
                "item": "comment",
                "post_id": "post-1",
                "comment_id": "comment-1",
                "message": "Nice video"
              }
            }]
          }]
        }
        """;

    WebhookEvent event = service.receiveWebhook(PlatformType.FACEBOOK, payload, "sha256=signature");

    assertThat(event.getEventType()).isEqualTo("meta.public_comment");
    assertThat(event.getPlatformPostId()).isEqualTo("post-1");
    assertThat(event.getIsProcessed()).isTrue();
    verify(publicationJobRepository, never()).findAll();
  }

  @Test
  void persistsInstagramCommentWebhookWithoutPublicationEventParsing() {
    String payload =
        """
        {
          "object": "instagram",
          "entry": [{
            "id": "ig-account-1",
            "changes": [{
              "field": "comments",
              "value": {
                "media": {"id": "media-1"},
                "id": "comment-1",
                "text": "Nice reel"
              }
            }]
          }]
        }
        """;

    WebhookEvent event =
        service.receiveWebhook(PlatformType.INSTAGRAM, payload, "sha256=signature");

    assertThat(event.getEventType()).isEqualTo("meta.public_comment");
    assertThat(event.getPlatformPostId()).isEqualTo("media-1");
    assertThat(event.getIsProcessed()).isTrue();
    verify(publicationJobRepository, never()).findAll();
  }

  @Test
  void routesCommentFromLaterMetaEntryWithoutPublicationLookup() {
    String payload =
        """
        {
          "object": "page",
          "entry": [
            {"id": "page-1", "changes": [{"field": "feed", "value": {"item": "status"}}]},
            {"id": "page-2", "changes": [{"field": "feed", "value": {"item": "comment", "post_id": "post-2", "comment_id": "comment-2", "message": "Later comment"}}]}
          ]
        }
        """;

    WebhookEvent event = service.receiveWebhook(PlatformType.FACEBOOK, payload, "sha256=signature");

    assertThat(event.getEventType()).isEqualTo("meta.public_comment");
    assertThat(event.getPlatformPostId()).isEqualTo("post-2");
    verify(publicationJobRepository, never()).findAll();
  }
}
