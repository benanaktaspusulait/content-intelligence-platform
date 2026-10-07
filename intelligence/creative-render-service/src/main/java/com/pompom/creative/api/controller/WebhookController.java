package com.pompom.creative.api.controller;

import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.meta.MetaPublicCommentIngestionService;
import com.pompom.creative.meta.MetaPublicCommentWebhookNormalizer;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.webhook.WebhookService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for webhook endpoints. Receives callbacks from social media platforms. */
@RestController
@RequestMapping("/api/v1/webhooks")
@Slf4j
@RequiredArgsConstructor
public class WebhookController {

  private final WebhookService webhookService;

  @Value("${pompom.webhooks.tiktok.secret:}")
  private String tiktokWebhookSecret;

  @Value("${pompom.webhooks.youtube.secret:}")
  private String youtubeWebhookSecret;

  @Value("${pompom.webhooks.facebook.secret:}")
  private String facebookWebhookSecret;

  @Value("${pompom.webhooks.instagram.secret:}")
  private String instagramWebhookSecret;

  /** TikTok webhook endpoint. */
  @PostMapping("/tiktok")
  public ResponseEntity<Map<String, String>> handleTikTokWebhook(
      @RequestBody String payload,
      @RequestHeader(value = "X-TikTok-Signature", required = false) String signature) {
    log.info("Received TikTok webhook");

    try {
      // Verify signature if secret is configured
      if (tiktokWebhookSecret != null && !tiktokWebhookSecret.isEmpty()) {
        if (!webhookService.verifySignature(
            PlatformType.TIKTOK, payload, signature, tiktokWebhookSecret)) {
          log.warn("Invalid TikTok webhook signature");
          return ResponseEntity.status(401).body(Map.of("error", "Invalid signature"));
        }
      }

      webhookService.receiveWebhook(PlatformType.TIKTOK, payload, signature);

      return ResponseEntity.ok(Map.of("status", "received"));

    } catch (Exception e) {
      log.error("Failed to handle TikTok webhook", e);
      return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
    }
  }

  /** YouTube webhook endpoint. */
  @PostMapping("/youtube")
  public ResponseEntity<Map<String, String>> handleYouTubeWebhook(
      @RequestBody String payload,
      @RequestHeader(value = "X-Hub-Signature", required = false) String signature) {
    log.info("Received YouTube webhook");

    try {
      // Verify signature if secret is configured
      if (youtubeWebhookSecret != null && !youtubeWebhookSecret.isEmpty()) {
        if (!webhookService.verifySignature(
            PlatformType.YOUTUBE, payload, signature, youtubeWebhookSecret)) {
          log.warn("Invalid YouTube webhook signature");
          return ResponseEntity.status(401).body(Map.of("error", "Invalid signature"));
        }
      }

      webhookService.receiveWebhook(PlatformType.YOUTUBE, payload, signature);

      return ResponseEntity.ok(Map.of("status", "received"));

    } catch (Exception e) {
      log.error("Failed to handle YouTube webhook", e);
      return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
    }
  }

  /** Facebook webhook endpoint. */
  @PostMapping("/facebook")
  public ResponseEntity<Map<String, String>> handleFacebookWebhook(
      @RequestBody String payload,
      @RequestHeader(value = "X-Hub-Signature-256", required = false) String signature) {
    log.info("Received Facebook webhook");

    try {
      // Verify signature if secret is configured
      if (facebookWebhookSecret != null && !facebookWebhookSecret.isEmpty()) {
        if (!webhookService.verifySignature(
            PlatformType.FACEBOOK, payload, signature, facebookWebhookSecret)) {
          log.warn("Invalid Facebook webhook signature");
          return ResponseEntity.status(401).body(Map.of("error", "Invalid signature"));
        }
      }

      webhookService.receiveWebhook(PlatformType.FACEBOOK, payload, signature);

      return ResponseEntity.ok(Map.of("status", "received"));

    } catch (Exception e) {
      log.error("Failed to handle Facebook webhook", e);
      return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
    }
  }

  /** Instagram webhook endpoint. */
  @PostMapping("/instagram")
  public ResponseEntity<Map<String, String>> handleInstagramWebhook(
      @RequestBody String payload,
      @RequestHeader(value = "X-Hub-Signature-256", required = false) String signature) {
    log.info("Received Instagram webhook");

    try {
      // Verify signature if secret is configured
      if (instagramWebhookSecret != null && !instagramWebhookSecret.isEmpty()) {
        if (!webhookService.verifySignature(
            PlatformType.INSTAGRAM, payload, signature, instagramWebhookSecret)) {
          log.warn("Invalid Instagram webhook signature");
          return ResponseEntity.status(401).body(Map.of("error", "Invalid signature"));
        }
      }

      webhookService.receiveWebhook(PlatformType.INSTAGRAM, payload, signature);

      return ResponseEntity.ok(Map.of("status", "received"));

    } catch (Exception e) {
      log.error("Failed to handle Instagram webhook", e);
      return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
    }
  }

  /** Facebook webhook verification (GET request). Required for initial webhook setup. */
  @GetMapping("/facebook")
  public ResponseEntity<String> verifyFacebookWebhook(
      @RequestParam("hub.mode") String mode,
      @RequestParam("hub.challenge") String challenge,
      @RequestParam("hub.verify_token") String verifyToken) {
    log.info("Facebook webhook verification request");

    // Verify token should match configured secret
    if ("subscribe".equals(mode) && facebookWebhookSecret.equals(verifyToken)) {
      log.info("Facebook webhook verified");
      return ResponseEntity.ok(challenge);
    }

    log.warn("Facebook webhook verification failed");
    return ResponseEntity.status(403).body("Forbidden");
  }

  /** Get webhook event by ID. */
  @GetMapping("/{eventId}")
  public ResponseEntity<WebhookEvent> getWebhookEvent(@PathVariable UUID eventId) {
    return webhookService
        .getWebhookEvent(eventId)
        .map(ResponseEntity::ok)
        .orElse(ResponseEntity.notFound().build());
  }

  /** Get webhooks for publication job. */
  @GetMapping("/job/{jobId}")
  public ResponseEntity<List<WebhookEvent>> getWebhooksForJob(@PathVariable UUID jobId) {
    return ResponseEntity.ok(webhookService.getWebhooksForJob(jobId));
  }

  /** Get pending webhooks. */
  @GetMapping("/pending")
  public ResponseEntity<List<WebhookEvent>> getPendingWebhooks() {
    return ResponseEntity.ok(webhookService.getPendingWebhooks());
  }
}
