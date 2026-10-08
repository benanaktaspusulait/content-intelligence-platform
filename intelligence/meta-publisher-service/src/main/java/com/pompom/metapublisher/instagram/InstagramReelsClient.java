package com.pompom.metapublisher.instagram;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.metapublisher.MetaClientSupport;
import com.pompom.metapublisher.MetaProviderException;
import com.pompom.metapublisher.MetaPublisherProperties;
import com.pompom.metapublisher.storage.PublicMediaStorage;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.RetryPolicy;
import com.pompom.publishersupport.SecretRedactor;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class InstagramReelsClient {

  public static final int CAPTION_LIMIT = 2200;
  private static final Logger log = LoggerFactory.getLogger(InstagramReelsClient.class);

  private final MetaPublisherProperties properties;
  private final PublicMediaStorage storage;
  private final MetaClientSupport http;
  private final SecretRedactor redactor = new SecretRedactor();
  private final ProviderErrorMapper errorMapper = new ProviderErrorMapper();

  public InstagramReelsClient(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      MetaPublisherProperties properties,
      PublicMediaStorage storage) {
    this.properties = properties;
    this.storage = storage;
    this.http =
        new MetaClientSupport(
            builder,
            objectMapper,
            properties.maxAttempts(),
            properties.requestTimeout(),
            properties.uploadTimeout());
  }

  public PublishResult publish(PublishCommand command) {
    String token = properties.instagramAccessToken();
    String containerId = null;
    String mediaId = null;
    String requestId = null;
    PublicMediaStorage.HostedMedia hosted = null;
    try {
      if (token == null || token.isBlank()) {
        return failed(
            PublishErrorClass.AUTHENTICATION,
            "Instagram publishing credentials are not configured",
            null,
            null,
            null);
      }
      if (command.platformAccountId() == null || command.platformAccountId().isBlank()) {
        return failed(
            PublishErrorClass.VALIDATION, "Instagram account ID is required", null, null, null);
      }
      if (properties.instagramAccountId() == null
          || properties.instagramAccountId().isBlank()
          || !properties.instagramAccountId().equals(command.platformAccountId())) {
        return failed(
            PublishErrorClass.AUTHORIZATION,
            "Instagram account is not configured for this publisher",
            null,
            null,
            null);
      }
      hosted = storage.host(command).orElse(null);
      if (hosted == null || !PublicMediaStorage.isSafeHttpsUrl(hosted.url())) {
        return failed(
            PublishErrorClass.UNSUPPORTED,
            "Instagram publishing requires a public HTTPS video URL",
            null,
            null,
            null);
      }

      String mediaEdge = graph("/" + command.platformAccountId() + "/media");
      Map<String, String> container = new LinkedHashMap<>();
      container.put("media_type", "REELS");
      container.put("video_url", hosted.url());
      container.put("caption", truncateCaption(fullCaption(command)));
      container.put("share_to_feed", shareToFeed(command));
      MetaClientSupport.MetaResponse created =
          http.postForm(
              mediaEdge, token, container, RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);
      requestId = created.providerRequestId();
      containerId = text(created.body(), "id");
      if (containerId == null || containerId.isBlank()) {
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            "Instagram did not return a media container id",
            requestId,
            null,
            null);
      }

      waitUntilReady(containerId, token);
      MetaClientSupport.MetaResponse published =
          http.postForm(
              graph("/" + command.platformAccountId() + "/media_publish"),
              token,
              Map.of("creation_id", containerId),
              RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);
      requestId = firstNonBlank(published.providerRequestId(), requestId);
      mediaId = text(published.body(), "id");
      if (mediaId == null || mediaId.isBlank()) {
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            "Instagram did not return a published media id",
            requestId,
            null,
            containerId);
      }
      String permalink = lookupPermalink(mediaId, token);
      return new PublishResult(
          PublishStatus.COMPLETED, mediaId, null, permalink, requestId, null, null, false);
    } catch (MetaProviderException failure) {
      return failure.toResult(mediaId, containerId);
    } catch (RuntimeException failure) {
      return new PublishResult(
          PublishStatus.RECONCILIATION_REQUIRED,
          mediaId,
          null,
          null,
          requestId,
          PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
          redactor.redact("Instagram publish failed: " + failure.getMessage(), token),
          true);
    } finally {
      if (hosted != null && hosted.owned()) {
        storage.cleanup(hosted.url());
      }
    }
  }

  public PublishResult reconcile(String accountId, String providerPostId, String providerVideoId) {
    String token = properties.instagramAccessToken();
    String identity = firstNonBlank(providerPostId, providerVideoId);
    if (token == null
        || token.isBlank()
        || identity == null
        || properties.instagramAccountId() == null
        || !properties.instagramAccountId().equals(accountId)) {
      return new PublishResult(
          PublishStatus.RECONCILIATION_REQUIRED,
          providerPostId,
          providerVideoId,
          null,
          null,
          PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
          "Instagram provider identity could not be reconciled",
          true);
    }
    try {
      MetaClientSupport.MetaResponse response =
          http.get(
              graph("/" + identity + "?fields=id,permalink"),
              token,
              RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);
      String resolvedId = text(response.body(), "id");
      if (resolvedId == null || resolvedId.isBlank()) {
        return new PublishResult(
            PublishStatus.RECONCILIATION_REQUIRED,
            providerPostId,
            providerVideoId,
            null,
            response.providerRequestId(),
            PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
            "Instagram provider identity was not found",
            true);
      }
      return new PublishResult(
          PublishStatus.COMPLETED,
          providerPostId == null ? resolvedId : providerPostId,
          providerVideoId,
          text(response.body(), "permalink"),
          response.providerRequestId(),
          null,
          null,
          false);
    } catch (MetaProviderException failure) {
      return failure.toResult(providerPostId, providerVideoId);
    }
  }

  public static String truncateCaption(String caption) {
    if (caption == null || caption.length() <= CAPTION_LIMIT) {
      return caption == null ? "" : caption;
    }
    return caption.substring(0, CAPTION_LIMIT - 1).stripTrailing() + "…";
  }

  private void waitUntilReady(String containerId, String token) {
    long deadline = System.nanoTime() + Math.max(0, properties.pollTimeout().toNanos());
    while (true) {
      MetaClientSupport.MetaResponse response =
          http.get(
              graph("/" + containerId + "?fields=status_code,status"),
              token,
              RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);
      String code = text(response.body(), "status_code");
      if ("FINISHED".equalsIgnoreCase(code) || "PUBLISHED".equalsIgnoreCase(code)) {
        return;
      }
      if ("ERROR".equalsIgnoreCase(code) || "EXPIRED".equalsIgnoreCase(code)) {
        throw new MetaProviderException(
            redactor.redact(
                "Instagram media processing failed: " + text(response.body(), "status"), token),
            422,
            code,
            response.providerRequestId(),
            new ProviderErrorMapper.Classification(
                PublishErrorClass.PROVIDER_REJECTED, false, false));
      }
      if (System.nanoTime() >= deadline) {
        throw new MetaProviderException(
            "Instagram media processing timed out",
            response.providerRequestId(),
            new ProviderErrorMapper.Classification(
                PublishErrorClass.RECONCILIATION_REQUIRED, false, true),
            null);
      }
      sleep(properties.pollInterval());
    }
  }

  private String lookupPermalink(String mediaId, String token) {
    try {
      return text(
          http.get(
                  graph("/" + mediaId + "?fields=permalink"),
                  token,
                  RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED)
              .body(),
          "permalink");
    } catch (MetaProviderException failure) {
      log.debug("Instagram permalink lookup failed for media {}", mediaId);
      return null;
    }
  }

  private String fullCaption(PublishCommand command) {
    String caption = command.caption() == null ? "" : command.caption();
    if (command.hashtags().isEmpty()) {
      return caption;
    }
    StringBuilder result = new StringBuilder(caption);
    if (!caption.isEmpty() && !caption.endsWith("\n")) {
      result.append("\n\n");
    }
    for (String hashtag : command.hashtags()) {
      if (hashtag == null || hashtag.isBlank()) {
        continue;
      }
      String normalized = hashtag.startsWith("#") ? hashtag : "#" + hashtag;
      if (result.length() > 0 && result.charAt(result.length() - 1) != ' ') {
        result.append(' ');
      }
      result.append(normalized);
    }
    return result.toString().stripTrailing();
  }

  private String shareToFeed(PublishCommand command) {
    String configured = command.providerOptions().get("share_to_feed");
    return configured == null ? Boolean.toString(properties.shareToFeed()) : configured;
  }

  private PublishResult failed(
      PublishErrorClass errorClass,
      String message,
      String requestId,
      String postId,
      String videoId) {
    return new PublishResult(
        PublishStatus.FAILED,
        postId,
        videoId,
        null,
        requestId,
        errorClass.wireValue(),
        redactor.redact(message, properties.instagramAccessToken()),
        false);
  }

  private String graph(String path) {
    String base = properties.graphBaseUrl();
    if (base == null || base.isBlank()) {
      base = "https://graph.facebook.com";
    }
    base = base.replaceAll("/+$", "");
    String version = properties.graphVersion();
    if (version == null || version.isBlank()) {
      version = "v26.0";
    } else if (!version.startsWith("v")) {
      version = "v" + version;
    }
    return base + "/" + version + (path.startsWith("/") ? path : "/" + path);
  }

  private void sleep(Duration duration) {
    if (duration == null || duration.isZero() || duration.isNegative()) {
      return;
    }
    try {
      Thread.sleep(duration.toMillis());
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new MetaProviderException(
          "Instagram processing wait was interrupted",
          null,
          errorMapper.classify(failure),
          failure);
    }
  }

  private String text(JsonNode node, String field) {
    if (node == null || node.isMissingNode() || node.get(field) == null) {
      return null;
    }
    return node.get(field).asText(null);
  }

  private String firstNonBlank(String first, String second) {
    return first != null && !first.isBlank() ? first : second;
  }
}
