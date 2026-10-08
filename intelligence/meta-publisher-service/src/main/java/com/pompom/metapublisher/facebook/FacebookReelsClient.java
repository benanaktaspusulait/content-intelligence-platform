package com.pompom.metapublisher.facebook;

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
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class FacebookReelsClient {

  private static final Logger log = LoggerFactory.getLogger(FacebookReelsClient.class);
  private static final String COMPLETE = "complete";
  private static final String ERROR = "error";

  private final MetaPublisherProperties properties;
  private final MetaClientSupport http;
  private final SecretRedactor redactor = new SecretRedactor();
  private final ProviderErrorMapper errorMapper = new ProviderErrorMapper();

  public FacebookReelsClient(
      RestClient.Builder builder, ObjectMapper objectMapper, MetaPublisherProperties properties) {
    this.properties = properties;
    this.http =
        new MetaClientSupport(
            builder,
            objectMapper,
            properties.maxAttempts(),
            properties.requestTimeout(),
            properties.uploadTimeout());
  }

  public PublishResult publish(PublishCommand command) {
    String token = properties.facebookPageAccessToken();
    String videoId = null;
    String postId = null;
    String requestId = null;
    try {
      if (token == null || token.isBlank()) {
        return failed(
            PublishErrorClass.AUTHENTICATION,
            "Facebook publishing credentials are not configured",
            null,
            null,
            null);
      }
      if (command.platformAccountId() == null || command.platformAccountId().isBlank()) {
        return failed(
            PublishErrorClass.VALIDATION, "Facebook Page ID is required", null, null, null);
      }
      if (properties.facebookPageId() == null
          || properties.facebookPageId().isBlank()
          || !properties.facebookPageId().equals(command.platformAccountId())) {
        return failed(
            PublishErrorClass.AUTHORIZATION,
            "Facebook Page is not configured for this publisher",
            null,
            null,
            null);
      }
      if (!localAssetAvailable(command.assetReference())) {
        return failed(
            PublishErrorClass.VALIDATION, "Facebook asset file is not available", null, null, null);
      }
      String edge = graph("/" + command.platformAccountId() + "/video_reels");
      MetaClientSupport.MetaResponse start =
          http.postForm(
              edge,
              token,
              Map.of("upload_phase", "start"),
              RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);
      requestId = start.providerRequestId();
      videoId = text(start.body(), "video_id");
      if (videoId == null || videoId.isBlank()) {
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            "Facebook did not return a video id",
            requestId,
            null,
            null);
      }

      String uploadUrl = text(start.body(), "upload_url");
      if (uploadUrl == null || uploadUrl.isBlank()) {
        uploadUrl = properties.ruploadBaseUrl() + "/" + version() + "/" + videoId;
      }
      upload(command.assetReference(), uploadUrl, token, videoId);
      waitUntilReady(videoId, token);

      Map<String, String> finish = new LinkedHashMap<>();
      finish.put("upload_phase", "finish");
      finish.put("video_id", videoId);
      finish.put("video_state", "PUBLISHED");
      finish.put("description", fullCaption(command));
      if (properties.facebookReelTitle() != null && !properties.facebookReelTitle().isBlank()) {
        finish.put("title", properties.facebookReelTitle());
      }
      MetaClientSupport.MetaResponse completed =
          http.postForm(edge, token, finish, RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);
      requestId = firstNonBlank(completed.providerRequestId(), requestId);
      if (completed.body().has("success") && !completed.body().path("success").asBoolean()) {
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            "Facebook rejected the reel publish",
            requestId,
            null,
            videoId);
      }
      postId = text(completed.body(), "post_id");
      if (postId == null || postId.isBlank()) {
        postId = videoId;
      }
      String permalink = lookupPermalink(videoId, token);
      return new PublishResult(
          PublishStatus.COMPLETED, postId, videoId, permalink, requestId, null, null, false);
    } catch (MetaProviderException failure) {
      return failure.toResult(postId, videoId);
    } catch (IOException | RuntimeException failure) {
      String message = redactor.redact("Facebook publish failed: " + failure.getMessage(), token);
      return new PublishResult(
          PublishStatus.RECONCILIATION_REQUIRED,
          postId,
          videoId,
          null,
          requestId,
          PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
          message,
          true);
    }
  }

  public PublishResult reconcile(String accountId, String providerPostId, String providerVideoId) {
    String token = properties.facebookPageAccessToken();
    String identity = firstNonBlank(providerVideoId, providerPostId);
    if (token == null
        || token.isBlank()
        || identity == null
        || properties.facebookPageId() == null
        || !properties.facebookPageId().equals(accountId)) {
      return new PublishResult(
          PublishStatus.RECONCILIATION_REQUIRED,
          providerPostId,
          providerVideoId,
          null,
          null,
          PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
          "Facebook provider identity could not be reconciled",
          true);
    }
    try {
      MetaClientSupport.MetaResponse response =
          http.get(
              graph("/" + identity + "?fields=id,permalink_url"),
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
            "Facebook provider identity was not found",
            true);
      }
      return new PublishResult(
          PublishStatus.COMPLETED,
          providerPostId,
          providerVideoId == null ? resolvedId : providerVideoId,
          text(response.body(), "permalink_url"),
          response.providerRequestId(),
          null,
          null,
          false);
    } catch (MetaProviderException failure) {
      return failure.toResult(providerPostId, providerVideoId);
    }
  }

  private boolean localAssetAvailable(String assetReference) {
    if (PublicMediaStorage.isSafeHttpsUrl(assetReference)) {
      return true;
    }
    try {
      return Files.isRegularFile(Path.of(assetReference));
    } catch (RuntimeException ignored) {
      return false;
    }
  }

  private void upload(String assetReference, String uploadUrl, String token, String videoId)
      throws IOException {
    if (PublicMediaStorage.isSafeHttpsUrl(assetReference)) {
      MetaClientSupport.MetaResponse response =
          http.postUpload(
              uploadUrl,
              token,
              new byte[0],
              Map.of("file_url", assetReference),
              RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);
      ensureSuccess(response.body(), "Facebook rejected the hosted video upload", token);
      return;
    }

    Path path = Path.of(assetReference);
    if (!Files.exists(path) || !Files.isRegularFile(path)) {
      throw new IOException("Facebook asset file is not available");
    }
    byte[] bytes = Files.readAllBytes(path);
    MetaClientSupport.MetaResponse response =
        http.postUpload(
            uploadUrl,
            token,
            bytes,
            Map.of(
                "offset", "0",
                "file_size", Long.toString(bytes.length),
                "Content-Type", "application/octet-stream"),
            RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);
    ensureSuccess(response.body(), "Facebook rejected the video upload", token);
  }

  private void waitUntilReady(String videoId, String token) {
    long timeoutNanos = Math.max(0, properties.pollTimeout().toNanos());
    long deadline = System.nanoTime() + timeoutNanos;
    while (true) {
      MetaClientSupport.MetaResponse response =
          http.get(
              graph("/" + videoId + "?fields=status"),
              token,
              RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);
      JsonNode status = response.body().path("status");
      String uploading = text(status.path("uploading_phase"), "status");
      String processing = text(status.path("processing_phase"), "status");
      if (ERROR.equalsIgnoreCase(uploading) || ERROR.equalsIgnoreCase(processing)) {
        throw new MetaProviderException(
            redactor.redact("Facebook video processing failed", token),
            422,
            "processing_error",
            response.providerRequestId(),
            new ProviderErrorMapper.Classification(
                PublishErrorClass.PROVIDER_REJECTED, false, false));
      }
      if (COMPLETE.equalsIgnoreCase(processing)
          || "ready".equalsIgnoreCase(text(status, "video_status"))) {
        return;
      }
      if (System.nanoTime() >= deadline) {
        throw new MetaProviderException(
            "Facebook video processing timed out",
            response.providerRequestId(),
            new ProviderErrorMapper.Classification(
                PublishErrorClass.RECONCILIATION_REQUIRED, false, true),
            null);
      }
      sleep(properties.pollInterval());
    }
  }

  private String lookupPermalink(String videoId, String token) {
    try {
      return text(
          http.get(
                  graph("/" + videoId + "?fields=permalink_url"),
                  token,
                  RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED)
              .body(),
          "permalink_url");
    } catch (MetaProviderException failure) {
      log.debug("Facebook permalink lookup failed for video {}", videoId);
      return null;
    }
  }

  private void ensureSuccess(JsonNode body, String message, String token) {
    if (body.has("success") && !body.path("success").asBoolean()) {
      throw new MetaProviderException(
          redactor.redact(message, token),
          422,
          "provider_rejected",
          text(body, "fbtrace_id"),
          new ProviderErrorMapper.Classification(
              PublishErrorClass.PROVIDER_REJECTED, false, false));
    }
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
        redactor.redact(message, properties.facebookPageAccessToken()),
        false);
  }

  private String graph(String path) {
    String base = trimTrailingSlash(properties.graphBaseUrl());
    return base + "/" + version() + (path.startsWith("/") ? path : "/" + path);
  }

  private String version() {
    String value = properties.graphVersion();
    if (value == null || value.isBlank()) {
      return "v26.0";
    }
    return value.startsWith("v") ? value : "v" + value;
  }

  private void sleep(java.time.Duration duration) {
    if (duration == null || duration.isZero() || duration.isNegative()) {
      return;
    }
    try {
      Thread.sleep(duration.toMillis());
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new MetaProviderException(
          "Facebook processing wait was interrupted", null, errorMapper.classify(failure), failure);
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
      if (result.length() > 0 && result.charAt(result.length() - 1) != ' ') {
        result.append(' ');
      }
      result.append(hashtag.startsWith("#") ? hashtag : "#" + hashtag);
    }
    return result.toString().stripTrailing();
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

  private String trimTrailingSlash(String value) {
    if (value == null || value.isBlank()) {
      return "https://graph.facebook.com";
    }
    return value.replaceAll("/+$", "");
  }
}
