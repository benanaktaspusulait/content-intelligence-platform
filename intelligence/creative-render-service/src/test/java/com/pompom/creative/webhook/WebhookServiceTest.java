package com.pompom.creative.webhook;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class WebhookServiceTest {

  @Mock private WebhookEventRepository webhookEventRepository;

  @Mock private PublicationJobRepository publicationJobRepository;

  @InjectMocks private WebhookService webhookService;

  private ObjectMapper objectMapper;

  @BeforeEach
  void setUp() {
    objectMapper = new ObjectMapper();
    webhookService =
        new WebhookService(webhookEventRepository, publicationJobRepository, objectMapper);
  }

  @Test
  void receiveWebhook_validPayload_createsEvent() throws Exception {
    // Given
    PlatformType platform = PlatformType.TIKTOK;
    String payload = "{\"event\":\"published\",\"video_id\":\"video-123\"}";
    String signature = "test-signature";

    when(webhookEventRepository.save(any(WebhookEvent.class)))
        .thenAnswer(
            invocation -> {
              WebhookEvent event = invocation.getArgument(0);
              event.setId(UUID.randomUUID());
              return event;
            });

    when(publicationJobRepository.findAll()).thenReturn(List.of());

    // When
    WebhookEvent result = webhookService.receiveWebhook(platform, payload, signature);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getPlatform()).isEqualTo(platform);
    assertThat(result.getPayload()).isEqualTo(payload);
    assertThat(result.getSignature()).isEqualTo(signature);

    verify(webhookEventRepository, atLeastOnce()).save(any(WebhookEvent.class));
  }

  @Test
  void processWebhookEvent_publishedEvent_updatesJobStatus() throws Exception {
    // Given
    UUID jobId = UUID.randomUUID();
    String platformPostId = "post-123";

    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .platform(PlatformType.YOUTUBE)
            .platformPostId(platformPostId)
            .status(PublicationStatus.PROCESSING)
            .build();

    String payload =
        String.format(
            "{\"status\":\"published\",\"id\":\"%s\",\"post_url\":\"https://youtube.com/shorts/123\"}",
            platformPostId);

    WebhookEvent event =
        WebhookEvent.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.YOUTUBE)
            .eventType("published")
            .platformPostId(platformPostId)
            .payload(payload)
            .isProcessed(false)
            .build();

    when(publicationJobRepository.findAll()).thenReturn(List.of(job));
    when(webhookEventRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(publicationJobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // When
    webhookService.processWebhookEvent(event);

    // Then
    assertThat(event.getIsProcessed()).isTrue();
    assertThat(event.getPublicationJobId()).isEqualTo(jobId);
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.PUBLISHED);

    verify(publicationJobRepository).save(job);
  }

  @Test
  void processWebhookEvent_failedEvent_updatesJobToFailed() throws Exception {
    // Given
    UUID jobId = UUID.randomUUID();
    String platformPostId = "post-456";

    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .platformPostId(platformPostId)
            .status(PublicationStatus.UPLOADING)
            .build();

    String payload =
        String.format(
            "{\"status\":\"failed\",\"id\":\"%s\",\"error_message\":\"Upload failed\"}",
            platformPostId);

    WebhookEvent event =
        WebhookEvent.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.TIKTOK)
            .eventType("failed")
            .platformPostId(platformPostId)
            .payload(payload)
            .isProcessed(false)
            .build();

    when(publicationJobRepository.findAll()).thenReturn(List.of(job));
    when(webhookEventRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(publicationJobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // When
    webhookService.processWebhookEvent(event);

    // Then
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.FAILED);
    assertThat(job.getErrorMessage()).contains("Upload failed");
  }

  @Test
  void processWebhookEvent_noMatchingJob_marksProcessedAnyway() throws Exception {
    // Given
    String payload = "{\"status\":\"published\",\"id\":\"unknown-post\"}";

    WebhookEvent event =
        WebhookEvent.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.FACEBOOK)
            .eventType("published")
            .platformPostId("unknown-post")
            .payload(payload)
            .isProcessed(false)
            .build();

    when(publicationJobRepository.findAll()).thenReturn(List.of());
    when(webhookEventRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // When
    webhookService.processWebhookEvent(event);

    // Then
    assertThat(event.getIsProcessed()).isTrue();
    verify(publicationJobRepository, never()).save(any());
  }

  @Test
  void webhookEvent_canRetry_checksRetryCount() {
    // Given: Event with retries remaining
    WebhookEvent canRetry = WebhookEvent.builder().isProcessed(false).retryCount(1).build();

    // Given: Event with max retries reached
    WebhookEvent cannotRetry = WebhookEvent.builder().isProcessed(false).retryCount(3).build();

    // Given: Processed event
    WebhookEvent processed = WebhookEvent.builder().isProcessed(true).retryCount(0).build();

    // Then
    assertThat(canRetry.canRetry()).isTrue();
    assertThat(cannotRetry.canRetry()).isFalse();
    assertThat(processed.canRetry()).isFalse();
  }

  @Test
  void webhookEvent_markProcessed_setsFlags() {
    // Given
    WebhookEvent event = WebhookEvent.builder().isProcessed(false).build();

    // When
    event.markProcessed();

    // Then
    assertThat(event.getIsProcessed()).isTrue();
    assertThat(event.getProcessedAt()).isNotNull();
  }

  @Test
  void webhookEvent_markFailed_incrementsRetryCount() {
    // Given
    WebhookEvent event = WebhookEvent.builder().retryCount(0).build();

    // When
    event.markFailed("Test error");

    // Then
    assertThat(event.getRetryCount()).isEqualTo(1);
    assertThat(event.getProcessingError()).isEqualTo("Test error");
  }

  @Test
  void getPendingWebhooks_returnsUnprocessed() {
    // Given
    List<WebhookEvent> pending =
        List.of(
            WebhookEvent.builder().isProcessed(false).build(),
            WebhookEvent.builder().isProcessed(false).build());

    when(webhookEventRepository.findByIsProcessedFalse()).thenReturn(pending);

    // When
    List<WebhookEvent> result = webhookService.getPendingWebhooks();

    // Then
    assertThat(result).hasSize(2);
  }
}
