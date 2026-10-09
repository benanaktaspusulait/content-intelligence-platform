package com.pompom.creative.publisher.internal;

import com.pompom.creative.publisher.PlatformPublisher;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

/** Render-service adapter for the provider-neutral internal publisher contract. */
public final class InternalPublisherClient implements PlatformPublisher {
  private final String capability;
  private final String baseUrl;
  private final String internalToken;
  private final boolean enabled;
  private final RestClient client;

  public InternalPublisherClient(
      RestClient.Builder builder,
      String capability,
      String baseUrl,
      String internalToken,
      boolean enabled) {
    this.capability = capability;
    this.baseUrl = baseUrl;
    this.internalToken = internalToken;
    this.enabled = enabled;
    this.client = builder.baseUrl(baseUrl).build();
  }

  @Override
  public PublishResponse publish(PublishRequest request) {
    PublishResult result = post("/internal/v1/publish", command(request), PublishResult.class);
    return toResponse(result);
  }

  @Override
  public Optional<PublishResponse> reconcile(
      PublishRequest request, String platformPostId, String platformVideoId) {
    Map<String, Object> body =
        Map.of(
            "publicationAttemptId", uuid(request.getIdempotencyKey()),
            "capability", capability,
            "platformAccountId", request.getPlatformAccountId(),
            "providerPostId", platformPostId == null ? "" : platformPostId,
            "providerVideoId", platformVideoId == null ? "" : platformVideoId);
    PublishResult result = post("/internal/v1/reconcile", body, PublishResult.class);
    return Optional.of(toResponse(result));
  }

  @Override
  public String getPlatformName() {
    return capability;
  }

  @Override
  public boolean isConfigured() {
    return enabled && baseUrl != null && !baseUrl.isBlank();
  }

  private PublishCommand command(PublishRequest request) {
    Path asset = Path.of(request.getVideoPath());
    try {
      byte[] bytes = Files.readAllBytes(asset);
      String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
      return new PublishCommand(
          uuid(request.getIdempotencyKey() + ":job"),
          uuid(request.getIdempotencyKey() + ":attempt"),
          request.getIdempotencyKey(),
          request.getPlatformAccountId(),
          asset.toString(),
          hash,
          request.getTitle(),
          request.getCaption(),
          request.getHashtags(),
          Boolean.TRUE.equals(request.getIsPrivate()),
          Map.of());
    } catch (IOException | java.security.NoSuchAlgorithmException exception) {
      throw new IllegalStateException("Publisher asset cannot be fingerprinted", exception);
    }
  }

  private <T> T post(String path, Object body, Class<T> type) {
    return client
        .post()
        .uri(path)
        .contentType(MediaType.APPLICATION_JSON)
        .header("X-Publisher-Internal-Token", internalToken == null ? "" : internalToken)
        .header("X-Publisher-Caller-Enabled", Boolean.toString(enabled))
        .header("X-Publisher-Capability", capability)
        .body(body)
        .retrieve()
        .body(type);
  }

  private PublishResponse toResponse(PublishResult result) {
    boolean success = result != null && result.status() == PublishStatus.COMPLETED;
    return PublishResponse.builder()
        .success(success)
        .platformPostId(result == null ? null : result.providerPostId())
        .platformVideoId(result == null ? null : result.providerVideoId())
        .postUrl(result == null ? null : result.permalink())
        .status(result == null ? "FAILED" : result.status().wireValue())
        .message(result == null ? "Publisher returned no result" : result.message())
        .build();
  }

  private UUID uuid(String value) {
    return UUID.nameUUIDFromBytes(value.getBytes(StandardCharsets.UTF_8));
  }
}
