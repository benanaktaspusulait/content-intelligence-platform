package com.pompom.creative.api.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.meta.MetaPublicCommentIngestionService;
import com.pompom.creative.meta.MetaPublicCommentWebhookNormalizer;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import com.pompom.creative.webhook.WebhookService;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;

class WebhookCommentControllerTest {

  private final WebhookEventRepository eventRepository = mock(WebhookEventRepository.class);
  private final PublicationJobRepository publicationJobRepository =
      mock(PublicationJobRepository.class);
  private final MetaPublicCommentWebhookNormalizer normalizer =
      mock(MetaPublicCommentWebhookNormalizer.class);
  private final MetaPublicCommentIngestionService ingestion =
      mock(MetaPublicCommentIngestionService.class);
  private WebhookController controller;

  @BeforeEach
  void setUp() {
    when(eventRepository.findByDeliveryKey(any())).thenReturn(Optional.empty());
    when(eventRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(publicationJobRepository.findAll()).thenReturn(java.util.List.of());

    controller =
        new WebhookController(
            new WebhookService(eventRepository, publicationJobRepository, new ObjectMapper()),
            normalizer,
            ingestion);
    ReflectionTestUtils.setField(controller, "facebookWebhookSecret", "");
    ReflectionTestUtils.setField(controller, "metaSignatureRequired", false);
  }

  @Test
  void routesFacebookCommentPayloadThroughCanonicalIngestion() {
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
    var normalized =
        new MetaPublicCommentWebhookNormalizer.NormalizedComment(
            PlatformType.FACEBOOK,
            "page-1",
            "post-1",
            "comment-1",
            "Nice video",
            null,
            "author-1",
            "Author",
            null,
            null);
    when(normalizer.normalizeAll(payload)).thenReturn(java.util.List.of(normalized));

    var response = controller.handleFacebookWebhook(payload, null);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
    verify(normalizer).normalizeAll(eq(payload));
    verify(ingestion).ingest(normalized);
  }
}
