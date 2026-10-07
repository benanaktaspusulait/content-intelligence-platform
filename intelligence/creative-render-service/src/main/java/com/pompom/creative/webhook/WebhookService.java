package com.pompom.creative.webhook;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Webhook service for handling platform callbacks. Processes incoming webhook events and updates
 * publication status.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class WebhookService {

  private final WebhookEventRepository webhookEventRepository;
  private final PublicationJobRepository publicationJobRepository;
  private final ObjectMapper objectMapper;

  /**
   * Receive and store webhook event.
   *
   * @param platform Source platform
   * @param payload Event payload (JSON)
   * @param signature Webhook signature
   * @return Created webhook event
   */
  @Transactional
  public WebhookEvent receiveWebhook(PlatformType platform, String payload, String signature) {
    String deliveryKey = deliveryKey(platform, payload, signature);
    Optional<WebhookEvent> existing = webhookEventRepository.findByDeliveryKey(deliveryKey);
    if (existing.isPresent()) {
      return existing.get();
    }
    return receiveWebhook(platform, payload, signature, deliveryKey);
  }

  @Transactional
  private WebhookEvent receiveWebhook(
      PlatformType platform, String payload, String signature, String deliveryKey) {
    log.info("Received webhook: platform={}", platform);

    try {
      // Parse payload to extract event type and post ID
      JsonNode json = objectMapper.readTree(payload);

      String eventType = extractEventType(platform, json);
      String platformPostId = extractPostId(platform, json);

      // Create webhook event
      WebhookEvent event =
          WebhookEvent.builder()
              .platform(platform)
              .eventType(eventType)
              .platformPostId(platformPostId)
              .payload(payload)
              .signature(signature)
              .deliveryKey(deliveryKey)
              .isProcessed(false)
              .build();

      WebhookEvent saved = webhookEventRepository.save(event);

      log.info("Webhook event saved: id={}, eventType={}", saved.getId(), eventType);

      // Process immediately
      processWebhookEvent(saved);

      return saved;

    } catch (Exception e) {
      log.error("Failed to receive webhook: platform={}", platform, e);
      throw new RuntimeException("Failed to process webhook", e);
    }
  }

  /** Process a webhook event. */
  @Transactional
  public void processWebhookEvent(WebhookEvent event) {
    log.info("Processing webhook event: id={}, eventType={}", event.getId(), event.getEventType());

    try {
      JsonNode payload = objectMapper.readTree(event.getPayload());

      // Find related publication job by platform post ID
      Optional<PublicationJob> jobOpt = findPublicationJob(event.getPlatformPostId());

      if (jobOpt.isEmpty()) {
        log.warn(
            "No publication job found for webhook: platformPostId={}", event.getPlatformPostId());
        event.markProcessed(); // Mark as processed anyway
        webhookEventRepository.save(event);
        return;
      }

      PublicationJob job = jobOpt.get();
      event.setPublicationJobId(job.getId());

      // Handle different event types
      handleEvent(event, job, payload);

      // Mark event as processed
      event.markProcessed();
      webhookEventRepository.save(event);

      log.info("Webhook event processed: id={}", event.getId());

    } catch (Exception e) {
      log.error("Failed to process webhook event: id={}", event.getId(), e);
      event.markFailed(e.getMessage());
      webhookEventRepository.save(event);
    }
  }

  /** Handle webhook event based on type. */
  private void handleEvent(WebhookEvent event, PublicationJob job, JsonNode payload) {
    String eventType = event.getEventType();

    switch (eventType) {
      case "video.processing_complete":
      case "processing_complete":
        handleProcessingComplete(job, payload);
        break;

      case "video.published":
      case "published":
        handlePublished(job, payload);
        break;

      case "video.failed":
      case "failed":
        handleFailed(job, payload);
        break;

      default:
        log.debug("Unknown event type, ignoring: {}", eventType);
    }
  }

  /** Handle processing complete event. */
  private void handleProcessingComplete(PublicationJob job, JsonNode payload) {
    log.info("Video processing complete: jobId={}", job.getId());

    if (job.getStatus() == PublicationStatus.PROCESSING) {
      job.updateStatus(PublicationStatus.PUBLISHED);
      job.setProgressPercent(100);
      publicationJobRepository.save(job);
    }
  }

  /** Handle published event. */
  private void handlePublished(PublicationJob job, JsonNode payload) {
    log.info("Video published: jobId={}", job.getId());

    job.updateStatus(PublicationStatus.PUBLISHED);
    job.setProgressPercent(100);

    // Extract post URL if available
    if (payload.has("post_url")) {
      job.setPostUrl(payload.get("post_url").asText());
    }

    publicationJobRepository.save(job);
  }

  /** Handle failed event. */
  private void handleFailed(PublicationJob job, JsonNode payload) {
    log.warn("Video publishing failed: jobId={}", job.getId());

    String errorMessage = "Platform reported failure";
    if (payload.has("error_message")) {
      errorMessage = payload.get("error_message").asText();
    }

    job.updateStatus(PublicationStatus.FAILED);
    job.setErrorMessage(errorMessage);
    publicationJobRepository.save(job);
  }

  /** Find publication job by platform post ID. */
  private Optional<PublicationJob> findPublicationJob(String platformPostId) {
    if (platformPostId == null || platformPostId.isEmpty()) {
      return Optional.empty();
    }

    return publicationJobRepository.findAll().stream()
        .filter(
            job ->
                platformPostId.equals(job.getPlatformPostId())
                    || platformPostId.equals(job.getPlatformVideoId()))
        .findFirst();
  }

  /** Extract event type from payload. */
  private String extractEventType(PlatformType platform, JsonNode payload) {
    // Platform-specific extraction
    return switch (platform) {
      case TIKTOK -> payload.has("event") ? payload.get("event").asText() : "unknown";
      case YOUTUBE -> payload.has("status") ? payload.get("status").asText() : "unknown";
      case FACEBOOK, INSTAGRAM ->
          payload.has("entry") && payload.get("entry").size() > 0
              ? payload
                  .get("entry")
                  .get(0)
                  .get("messaging")
                  .get(0)
                  .get("message")
                  .get("text")
                  .asText()
              : "unknown";
    };
  }

  /** Extract post ID from payload. */
  private String extractPostId(PlatformType platform, JsonNode payload) {
    // Platform-specific extraction
    return switch (platform) {
      case TIKTOK -> payload.has("video_id") ? payload.get("video_id").asText() : null;
      case YOUTUBE -> payload.has("id") ? payload.get("id").asText() : null;
      case FACEBOOK, INSTAGRAM -> payload.has("post_id") ? payload.get("post_id").asText() : null;
    };
  }

  /** Verify webhook signature. */
  public boolean verifySignature(
      PlatformType platform, String payload, String signature, String secret) {
    try {
      if (payload == null
          || signature == null
          || signature.isBlank()
          || secret == null
          || secret.isBlank()) {
        return false;
      }
      String expectedSignature = generateSignature(payload, secret);
      String providedSignature = signature.trim();
      if (providedSignature.regionMatches(true, 0, "sha256=", 0, 7)) {
        providedSignature = providedSignature.substring(7);
      }
      return MessageDigest.isEqual(
          expectedSignature.getBytes(StandardCharsets.UTF_8),
          providedSignature.getBytes(StandardCharsets.UTF_8));
    } catch (Exception e) {
      log.error("Failed to verify signature", e);
      return false;
    }
  }

  private String deliveryKey(PlatformType platform, String payload, String signature) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      byte[] value =
          digest.digest(
              (platform.name() + ":" + (signature == null ? "" : signature) + ":" + payload)
                  .getBytes(StandardCharsets.UTF_8));
      return java.util.HexFormat.of().formatHex(value);
    } catch (NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    }
  }

  /** Generate HMAC-SHA256 signature. */
  private String generateSignature(String payload, String secret)
      throws NoSuchAlgorithmException, InvalidKeyException {

    Mac mac = Mac.getInstance("HmacSHA256");
    SecretKeySpec secretKeySpec =
        new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
    mac.init(secretKeySpec);

    byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
    return Base64.getEncoder().encodeToString(hash);
  }

  /** Retry failed webhooks. Runs every 15 minutes. */
  @Scheduled(cron = "0 */15 * * * *")
  @Transactional
  public void retryFailedWebhooks() {
    log.debug("Retrying failed webhook events");

    List<WebhookEvent> failed =
        webhookEventRepository.findByIsProcessedFalseAndRetryCountLessThan(3);

    if (failed.isEmpty()) {
      return;
    }

    log.info("Found {} failed webhooks to retry", failed.size());

    for (WebhookEvent event : failed) {
      if (event.canRetry()) {
        try {
          processWebhookEvent(event);
        } catch (Exception e) {
          log.error("Retry failed for webhook: id={}", event.getId(), e);
        }
      }
    }
  }

  /** Get webhook event by ID. */
  @Transactional(readOnly = true)
  public Optional<WebhookEvent> getWebhookEvent(UUID eventId) {
    return webhookEventRepository.findById(eventId);
  }

  /** Get webhooks for publication job. */
  @Transactional(readOnly = true)
  public List<WebhookEvent> getWebhooksForJob(UUID jobId) {
    return webhookEventRepository.findByPublicationJobId(jobId);
  }

  /** Get pending webhooks. */
  @Transactional(readOnly = true)
  public List<WebhookEvent> getPendingWebhooks() {
    return webhookEventRepository.findByIsProcessedFalse();
  }
}
