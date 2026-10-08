package com.pompom.tiktokpublisher.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.RetryPolicy;
import com.pompom.publishersupport.SecretRedactor;
import com.pompom.tiktokpublisher.TikTokPublisherProperties;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** TikTok Content Posting API adapter; it never treats upload acceptance as publication. */
@Component
public class TikTokContentClient {

  public static final int CAPTION_LIMIT = 2200;
  public static final String VIDEO_CONTENT_TYPE = "video/mp4";
  public static final String CREATOR_INFO_PATH = "/post/publish/creator_info/query/";
  public static final String INIT_PATH = "/post/publish/video/init/";
  public static final String STATUS_PATH = "/post/publish/status/fetch/";

  private final RestClient restClient;
  private final ObjectMapper objectMapper;
  private final TikTokPublisherProperties properties;
  private final ProviderErrorMapper errorMapper = new ProviderErrorMapper();
  private final SecretRedactor redactor = new SecretRedactor();
  private final RetryPolicy retryPolicy;

  @Autowired
  public TikTokContentClient(
      RestClient.Builder builder, ObjectMapper objectMapper, TikTokPublisherProperties properties) {
    this.restClient = builder.build();
    this.objectMapper = Objects.requireNonNull(objectMapper, "objectMapper");
    this.properties = Objects.requireNonNull(properties, "properties");
    requireHttpsEndpoint(properties.apiBaseUrl(), "apiBaseUrl");
    this.retryPolicy =
        new RetryPolicy(
            properties.maxAttempts(),
            RetryPolicy.DEFAULT_INITIAL_BACKOFF,
            RetryPolicy.DEFAULT_MAX_BACKOFF);
  }

  public TikTokContentClient(
      RestClient restClient, ObjectMapper objectMapper, TikTokPublisherProperties properties) {
    this.restClient = Objects.requireNonNull(restClient, "restClient");
    this.objectMapper = Objects.requireNonNull(objectMapper, "objectMapper");
    this.properties = Objects.requireNonNull(properties, "properties");
    requireHttpsEndpoint(properties.apiBaseUrl(), "apiBaseUrl");
    this.retryPolicy =
        new RetryPolicy(
            properties.maxAttempts(),
            RetryPolicy.DEFAULT_INITIAL_BACKOFF,
            RetryPolicy.DEFAULT_MAX_BACKOFF);
  }

  /** Creates bounded request factories with independent API and signed-upload deadlines. */
  public static ClientHttpRequestFactory deadlineRequestFactory(
      TikTokPublisherProperties properties) {
    Objects.requireNonNull(properties, "properties");
    Duration requestTimeout = positive(properties.requestTimeout(), Duration.ofSeconds(120));
    Duration uploadTimeout = positive(properties.uploadTimeout(), Duration.ofSeconds(600));
    JdkClientHttpRequestFactory apiFactory =
        new JdkClientHttpRequestFactory(
            HttpClient.newBuilder().connectTimeout(requestTimeout).build());
    apiFactory.setReadTimeout(requestTimeout);
    JdkClientHttpRequestFactory uploadFactory =
        new JdkClientHttpRequestFactory(
            HttpClient.newBuilder().connectTimeout(uploadTimeout).build());
    uploadFactory.setReadTimeout(uploadTimeout);
    URI apiBase = URI.create(properties.apiBaseUrl());
    return (uri, method) ->
        isUploadUri(uri, apiBase, properties.apiVersion())
            ? uploadFactory.createRequest(uri, method)
            : apiFactory.createRequest(uri, method);
  }

  public PublishResult publish(PublishCommand command) {
    String publishId = null;
    String providerRequestId = null;
    try {
      PublishCommand normalizedCommand = normalizeCommand(command);
      Asset asset = validateAsset(normalizedCommand.assetReference());

      if (properties.creatorValidationEnabled()) {
        ProviderResponse creatorResponse =
            execute(
                () -> postJson(apiEndpoint(CREATOR_INFO_PATH), objectMapper.createObjectNode()),
                RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED,
                "creator validation");
        providerRequestId = creatorResponse.providerRequestId();
        validateCreatorResponse(creatorResponse);
      }

      InitResponse init = initialize(normalizedCommand, asset);
      publishId = init.publishId();
      providerRequestId = firstNonBlank(init.providerRequestId(), providerRequestId);

      upload(asset.path(), init.uploadUrl(), asset.size());
      return pollUntilTerminal(publishId, providerRequestId);
    } catch (TikTokValidationException failure) {
      return failed(
          PublishErrorClass.VALIDATION, failure.getMessage(), providerRequestId, publishId);
    } catch (TikTokProviderException failure) {
      return mapFailure(failure, publishId);
    } catch (IOException | RuntimeException failure) {
      String message =
          redactor.redact(
              "TikTok publish failed: " + failure.getMessage(), properties.accessToken());
      if (publishId != null) {
        return reconciliationRequired(publishId, providerRequestId, message);
      }
      return reconciliationRequired(null, providerRequestId, message);
    }
  }

  /** Performs only a read-only status lookup for a known TikTok publish ID. */
  public PublishResult reconcile(String publishId) {
    if (!isSafeIdentifier(publishId)) {
      return reconciliationRequired(null, null, "TikTok publish identity is invalid");
    }
    try {
      return pollUntilTerminal(publishId, null);
    } catch (TikTokProviderException failure) {
      return reconciliationRequired(
          publishId,
          failure.providerRequestId(),
          redactor.redact(failure.getMessage(), properties.accessToken()));
    } catch (RuntimeException failure) {
      return reconciliationRequired(
          publishId,
          null,
          redactor.redact(
              "TikTok reconciliation failed: " + failure.getMessage(), properties.accessToken()));
    }
  }

  /** Checks the provider-owned creator boundary without starting a publication. */
  public PublishResult validateCreator() {
    try {
      ProviderResponse response =
          execute(
              () -> postJson(apiEndpoint(CREATOR_INFO_PATH), objectMapper.createObjectNode()),
              RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED,
              "creator validation");
      validateCreatorResponse(response);
      return new PublishResult(
          PublishStatus.COMPLETED,
          null,
          null,
          null,
          response.providerRequestId(),
          null,
          null,
          false);
    } catch (TikTokProviderException failure) {
      return mapFailure(failure, null);
    } catch (RuntimeException failure) {
      return reconciliationRequired(
          null,
          null,
          redactor.redact(
              "TikTok creator validation failed: " + failure.getMessage(),
              properties.accessToken()));
    }
  }

  private InitResponse initialize(PublishCommand command, Asset asset)
      throws TikTokProviderException {
    ObjectNode body = objectMapper.createObjectNode();
    ObjectNode postInfo = body.putObject("post_info");
    String caption = fullCaption(command);
    if (!caption.isBlank()) {
      postInfo.put("title", caption);
    }
    postInfo.put("privacy_level", privacyLevel(command));
    postInfo.put("disable_duet", booleanOption(command, "disable_duet", properties.disableDuet()));
    postInfo.put(
        "disable_comment", booleanOption(command, "disable_comment", properties.disableComment()));
    postInfo.put(
        "disable_stitch", booleanOption(command, "disable_stitch", properties.disableStitch()));
    postInfo.put(
        "video_cover_timestamp_ms",
        longOption(command, "video_cover_timestamp_ms", properties.videoCoverTimestampMs()));

    ObjectNode sourceInfo = body.putObject("source_info");
    sourceInfo.put("source", "FILE_UPLOAD");
    sourceInfo.put("video_size", asset.size());
    sourceInfo.put("chunk_size", properties.chunkSize());
    sourceInfo.put("total_chunk_count", chunkCount(asset.size(), properties.chunkSize()));

    ProviderResponse response =
        execute(
            () -> postJson(apiEndpoint(INIT_PATH), body),
            RetryPolicy.SubmissionPhase.SUBMISSION_STARTED,
            "video initialization");
    JsonNode data = response.body().path("data");
    String publishId = text(data, "publish_id");
    String uploadUrl = text(data, "upload_url");
    if (!isSafeIdentifier(publishId) || uploadUrl == null || uploadUrl.isBlank()) {
      throw new TikTokProviderException(
          "TikTok initialization returned no upload identity",
          response.providerRequestId(),
          new ProviderErrorMapper.Classification(
              PublishErrorClass.PROVIDER_REJECTED, false, false));
    }
    requireHttpsUploadUrl(uploadUrl);
    return new InitResponse(publishId, uploadUrl, response.providerRequestId());
  }

  private void upload(Path path, String uploadUrl, long fileSize)
      throws IOException, TikTokProviderException {
    if (fileSize <= 0) {
      throw new TikTokValidationException("TikTok video file must not be empty");
    }
    long uploaded = 0;
    try (InputStream input = Files.newInputStream(path)) {
      while (uploaded < fileSize) {
        int requested = (int) Math.min(properties.chunkSize(), fileSize - uploaded);
        byte[] chunk = input.readNBytes(requested);
        if (chunk.length != requested) {
          throw new IOException("TikTok asset changed while it was being uploaded");
        }
        long end = uploaded + chunk.length - 1;
        final long chunkStart = uploaded;
        final long chunkEnd = end;
        ProviderResponse uploadResponse =
            execute(
                () ->
                    putUpload(
                        uploadUrl, chunk, "bytes " + chunkStart + "-" + chunkEnd + "/" + fileSize),
                RetryPolicy.SubmissionPhase.SUBMISSION_STARTED,
                "video chunk upload",
                properties.uploadTimeout());
        if (uploadResponse.status() != 200
            && uploadResponse.status() != 201
            && uploadResponse.status() != 204) {
          throw new TikTokProviderException(
              "TikTok chunk upload returned an unsupported response status",
              uploadResponse.providerRequestId(),
              errorMapper.classify(uploadResponse.status()));
        }
        uploaded = end + 1;
      }
    }
  }

  private PublishResult pollUntilTerminal(String publishId, String initialRequestId)
      throws TikTokProviderException {
    long deadline = deadlineNanos(properties.pollTimeout());
    String requestId = initialRequestId;
    while (true) {
      if (deadlineExceeded(deadline)) {
        return reconciliationRequired(
            publishId, requestId, "TikTok publication status polling timed out");
      }
      ProviderResponse response =
          execute(
              () -> {
                ObjectNode body = objectMapper.createObjectNode();
                body.put("publish_id", publishId);
                return postJson(apiEndpoint(STATUS_PATH), body);
              },
              RetryPolicy.SubmissionPhase.SUBMISSION_STARTED,
              "publication status",
              properties.requestTimeout(),
              deadline);
      requestId = firstNonBlank(response.providerRequestId(), requestId);
      JsonNode data = response.body().path("data");
      String returnedPublishId = text(data, "publish_id");
      String status = text(data, "status");

      if ("PUBLISH_COMPLETE".equals(status)) {
        if (!publishId.equals(returnedPublishId)) {
          return reconciliationRequired(
              publishId,
              requestId,
              "TikTok completion evidence did not match the requested publish identity");
        }
        return new PublishResult(
            PublishStatus.COMPLETED,
            publishId,
            null,
            nonBlank(text(data, "share_url")),
            requestId,
            null,
            null,
            false);
      }
      if ("FAILED".equals(status)) {
        if (!publishId.equals(returnedPublishId)) {
          return reconciliationRequired(
              publishId,
              requestId,
              "TikTok failure evidence did not match the requested publish identity");
        }
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            nonBlank(text(data, "fail_reason"), "TikTok rejected the video"),
            requestId,
            publishId);
      }

      if (deadlineExceeded(deadline)) {
        return reconciliationRequired(
            publishId, requestId, "TikTok publication status polling timed out");
      }
      Duration remaining = remaining(deadline);
      if (remaining.isZero() || remaining.isNegative()) {
        return reconciliationRequired(
            publishId, requestId, "TikTok publication status polling timed out");
      }
      sleep(bounded(properties.pollInterval(), remaining));
    }
  }

  private ProviderResponse postJson(String url, JsonNode body) {
    return restClient
        .post()
        .uri(URI.create(url))
        .headers(headers -> applyJsonHeaders(headers, properties.accessToken()))
        .contentType(MediaType.APPLICATION_JSON)
        .body(body.toString())
        .exchange(this::parseResponse);
  }

  private ProviderResponse putUpload(String url, byte[] body, String contentRange) {
    return restClient
        .put()
        .uri(URI.create(url))
        .headers(
            headers -> {
              headers.set(HttpHeaders.CONTENT_TYPE, VIDEO_CONTENT_TYPE);
              headers.set(HttpHeaders.CONTENT_RANGE, contentRange);
            })
        .body(body)
        .exchange(this::parseResponse);
  }

  private ProviderResponse execute(
      Supplier<ProviderResponse> operation,
      RetryPolicy.SubmissionPhase submissionPhase,
      String operationName)
      throws TikTokProviderException {
    return execute(
        operation, submissionPhase, operationName, properties.requestTimeout(), Long.MAX_VALUE);
  }

  private ProviderResponse execute(
      Supplier<ProviderResponse> operation,
      RetryPolicy.SubmissionPhase submissionPhase,
      String operationName,
      Duration operationTimeout)
      throws TikTokProviderException {
    return execute(operation, submissionPhase, operationName, operationTimeout, Long.MAX_VALUE);
  }

  private ProviderResponse execute(
      Supplier<ProviderResponse> operation,
      RetryPolicy.SubmissionPhase submissionPhase,
      String operationName,
      Duration operationTimeout,
      long deadlineNanos)
      throws TikTokProviderException {
    TikTokProviderException lastFailure = null;
    for (int attempt = 1; attempt <= properties.maxAttempts(); attempt++) {
      Duration remaining = remaining(deadlineNanos);
      if (remaining.isZero() || remaining.isNegative()) {
        throw timeoutFailure(operationName);
      }
      Duration timeout = bounded(operationTimeout, remaining);
      if (timeout.isZero() || timeout.isNegative()) {
        throw timeoutFailure(operationName);
      }
      try {
        return runWithTimeout(operation, timeout, operationName);
      } catch (TikTokProviderException failure) {
        lastFailure = failure;
        RetryPolicy.Decision decision =
            retryPolicy.decide(failure.classification(), attempt, submissionPhase);
        if (!decision.shouldRetry() || attempt == properties.maxAttempts()) {
          throw failure;
        }
        if (!canWaitForRetry(decision.backoff(), deadlineNanos)) {
          throw timeoutFailure(operationName);
        }
        sleep(bounded(decision.backoff(), remaining(deadlineNanos)));
      } catch (RestClientException failure) {
        ProviderErrorMapper.Classification classification = errorMapper.classify(failure);
        lastFailure =
            new TikTokProviderException(
                redactor.redact(
                    "TikTok " + operationName + " failed: " + failure.getMessage(),
                    properties.accessToken()),
                null,
                classification,
                failure);
        RetryPolicy.Decision decision =
            retryPolicy.decide(classification, attempt, submissionPhase);
        if (!decision.shouldRetry() || attempt == properties.maxAttempts()) {
          throw lastFailure;
        }
        if (!canWaitForRetry(decision.backoff(), deadlineNanos)) {
          throw timeoutFailure(operationName);
        }
        sleep(bounded(decision.backoff(), remaining(deadlineNanos)));
      }
    }
    throw lastFailure == null
        ? new TikTokProviderException(
            "TikTok " + operationName + " ended without a result",
            null,
            new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true))
        : lastFailure;
  }

  private ProviderResponse runWithTimeout(
      Supplier<ProviderResponse> operation, Duration timeout, String operationName) {
    ExecutorService executor =
        Executors.newSingleThreadExecutor(
            runnable -> {
              Thread thread = new Thread(runnable, "tiktok-provider-timeout");
              thread.setDaemon(true);
              return thread;
            });
    Future<ProviderResponse> future = executor.submit(operation::get);
    try {
      return future.get(timeout.toNanos(), TimeUnit.NANOSECONDS);
    } catch (TimeoutException failure) {
      future.cancel(true);
      throw new TikTokProviderException(
          "TikTok " + operationName + " timed out",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true),
          failure);
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new TikTokProviderException(
          "TikTok " + operationName + " was interrupted",
          null,
          errorMapper.classify(failure),
          failure);
    } catch (ExecutionException failure) {
      Throwable cause = failure.getCause();
      if (cause instanceof RuntimeException runtimeException) {
        throw runtimeException;
      }
      if (cause instanceof Error error) {
        throw error;
      }
      throw new RestClientException("TikTok " + operationName + " failed", cause);
    } finally {
      executor.shutdownNow();
    }
  }

  private TikTokProviderException timeoutFailure(String operationName) {
    return new TikTokProviderException(
        "TikTok " + operationName + " timed out",
        null,
        new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true));
  }

  private boolean canWaitForRetry(Duration wait, long deadlineNanos) {
    return deadlineNanos == Long.MAX_VALUE || wait.compareTo(remaining(deadlineNanos)) < 0;
  }

  private ProviderResponse parseResponse(
      org.springframework.http.HttpRequest request, ClientHttpResponse response) {
    try {
      String raw =
          response.getBody() == null
              ? ""
              : StreamUtils.copyToString(response.getBody(), StandardCharsets.UTF_8);
      int status = response.getStatusCode().value();
      JsonNode body = parseBody(raw, status);
      String requestId =
          firstNonBlank(
              response.getHeaders().getFirst("x-tt-logid"),
              response.getHeaders().getFirst("x-tt-request-id"),
              text(body, "log_id"),
              text(body.path("error"), "log_id"));
      if (status >= 400) {
        throw providerFailure(status, body, requestId);
      }
      String errorCode = text(body.path("error"), "code");
      if (errorCode != null && !errorCode.isBlank() && !"ok".equalsIgnoreCase(errorCode)) {
        throw new TikTokProviderException(
            redactor.redact(
                nonBlank(text(body.path("error"), "message"), "TikTok provider returned an error"),
                properties.accessToken()),
            requestId,
            errorMapper.classify(status, errorCode));
      }
      return new ProviderResponse(body, requestId, status);
    } catch (IOException failure) {
      throw new TikTokProviderException(
          redactor.redact(
              "TikTok response could not be read: " + failure.getMessage(),
              properties.accessToken()),
          null,
          errorMapper.classify(failure),
          failure);
    }
  }

  private JsonNode parseBody(String raw, int status) throws IOException {
    if (raw == null || raw.isBlank()) {
      return MissingNode.getInstance();
    }
    try {
      JsonNode body = objectMapper.readTree(raw);
      return body == null ? MissingNode.getInstance() : body;
    } catch (IOException failure) {
      if (status >= 400) {
        return MissingNode.getInstance();
      }
      throw failure;
    }
  }

  private TikTokProviderException providerFailure(int status, JsonNode body, String requestId) {
    String message = text(body.path("error"), "message");
    if (message == null || message.isBlank()) {
      message = "TikTok provider request failed (HTTP " + status + ")";
    }
    String code = text(body.path("error"), "code");
    return new TikTokProviderException(
        redactor.redact(message, properties.accessToken()),
        requestId,
        status >= 500
            ? new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true)
            : errorMapper.classify(status, code));
  }

  private void validateCreatorResponse(ProviderResponse response) throws TikTokProviderException {
    JsonNode data = response.body().path("data");
    if (!data.isObject() || data.isEmpty() || properties.platformAccountId().isBlank()) {
      throw new TikTokProviderException(
          "TikTok creator validation returned no creator data",
          response.providerRequestId(),
          new ProviderErrorMapper.Classification(PublishErrorClass.AUTHORIZATION, false, false));
    }

    String identity =
        firstNonBlank(
            text(data, "creator_open_id"),
            text(data, "open_id"),
            text(data, "creator_id"),
            text(data, "account_id"),
            text(data, "platform_account_id"));
    boolean identityFieldPresent =
        data.has("creator_open_id")
            || data.has("open_id")
            || data.has("creator_id")
            || data.has("account_id")
            || data.has("platform_account_id");
    if (identityFieldPresent
        && (identity == null || !properties.platformAccountId().equals(identity))) {
      throw new TikTokProviderException(
          "TikTok creator validation identity does not match the configured account",
          response.providerRequestId(),
          new ProviderErrorMapper.Classification(PublishErrorClass.AUTHORIZATION, false, false));
    }
  }

  private PublishResult mapFailure(TikTokProviderException failure, String publishId) {
    String message = redactor.redact(failure.getMessage(), properties.accessToken());
    PublishErrorClass errorClass = failure.classification().errorClass();
    if (publishId != null && failure.classification().uncertainAfterSubmission()) {
      return reconciliationRequired(publishId, failure.providerRequestId(), message);
    }
    if (errorClass == PublishErrorClass.TRANSIENT || errorClass == PublishErrorClass.UNKNOWN) {
      return reconciliationRequired(publishId, failure.providerRequestId(), message);
    }
    return failed(errorClass, message, failure.providerRequestId(), publishId);
  }

  private PublishResult failed(
      PublishErrorClass errorClass, String message, String providerRequestId, String publishId) {
    PublishErrorClass normalized =
        errorClass == null
                || errorClass == PublishErrorClass.TRANSIENT
                || errorClass == PublishErrorClass.UNKNOWN
                || errorClass == PublishErrorClass.RECONCILIATION_REQUIRED
            ? PublishErrorClass.PROVIDER_REJECTED
            : errorClass;
    return new PublishResult(
        PublishStatus.FAILED,
        publishId,
        null,
        null,
        providerRequestId,
        normalized.wireValue(),
        redactor.redact(message, properties.accessToken()),
        false);
  }

  private PublishResult reconciliationRequired(
      String publishId, String providerRequestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        publishId,
        null,
        null,
        providerRequestId,
        PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
        redactor.redact(message, properties.accessToken()),
        true);
  }

  private PublishCommand normalizeCommand(PublishCommand command) {
    if (command == null) {
      throw new TikTokValidationException("publish command is required");
    }
    String caption = truncateCaption(command.caption());
    if (Objects.equals(caption, command.caption())) {
      return command;
    }
    return new PublishCommand(
        command.publicationJobId(),
        command.publicationAttemptId(),
        command.idempotencyKey(),
        command.platformAccountId(),
        command.assetReference(),
        command.assetSha256(),
        command.title(),
        caption,
        command.hashtags(),
        command.isPrivate(),
        command.providerOptions());
  }

  public static String truncateCaption(String caption) {
    if (caption == null || caption.codePointCount(0, caption.length()) <= CAPTION_LIMIT) {
      return caption;
    }
    int end = caption.offsetByCodePoints(0, CAPTION_LIMIT - 1);
    return caption.substring(0, end) + "…";
  }

  private Asset validateAsset(String assetReference) {
    if (assetReference == null || assetReference.isBlank()) {
      throw new TikTokValidationException("TikTok asset reference is required");
    }
    Path path;
    try {
      path = Path.of(assetReference);
    } catch (RuntimeException failure) {
      throw new TikTokValidationException("TikTok asset reference is invalid");
    }
    if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
      throw new TikTokValidationException("TikTok video file is not available");
    }
    long size;
    try {
      size = Files.size(path);
    } catch (IOException failure) {
      throw new TikTokValidationException("TikTok video file cannot be read");
    }
    if (size <= 0) {
      throw new TikTokValidationException("TikTok video file must not be empty");
    }
    if (size > properties.maxFileSize()) {
      throw new TikTokValidationException(
          "TikTok video file exceeds the maximum size of " + properties.maxFileSize() + " bytes");
    }
    return new Asset(path, size);
  }

  private String fullCaption(PublishCommand command) {
    StringBuilder value = new StringBuilder();
    if (command.caption() != null && !command.caption().isBlank()) {
      value.append(command.caption().trim());
    } else if (command.title() != null && !command.title().isBlank()) {
      value.append(command.title().trim());
    }
    for (String hashtag : command.hashtags()) {
      if (hashtag == null || hashtag.isBlank()) {
        continue;
      }
      if (!value.isEmpty()) {
        value.append(' ');
      }
      value.append(hashtag.startsWith("#") ? hashtag : "#" + hashtag);
    }
    return truncateCaption(value.toString());
  }

  private String privacyLevel(PublishCommand command) {
    String configured =
        firstNonBlank(
            command.providerOptions().get("privacy_level"),
            command.providerOptions().get("privacy"),
            command.providerOptions().get("privacy_status"));
    if (configured != null) {
      return configured;
    }
    return command.isPrivate() ? "SELF_ONLY" : properties.privacyLevel();
  }

  private boolean booleanOption(PublishCommand command, String key, boolean fallback) {
    String value = command.providerOptions().get(key);
    return value == null || value.isBlank() ? fallback : Boolean.parseBoolean(value);
  }

  private long longOption(PublishCommand command, String key, long fallback) {
    String value = command.providerOptions().get(key);
    if (value == null || value.isBlank()) {
      return fallback;
    }
    try {
      return Long.parseLong(value);
    } catch (NumberFormatException failure) {
      throw new TikTokValidationException("TikTok option " + key + " must be a number");
    }
  }

  private String apiEndpoint(String path) {
    String base = trimTrailingSlash(properties.apiBaseUrl());
    String version = trimSlashes(properties.apiVersion());
    return base + "/" + version + (path.startsWith("/") ? path : "/" + path);
  }

  private void applyJsonHeaders(HttpHeaders headers, String token) {
    headers.setContentType(MediaType.APPLICATION_JSON);
    headers.setBearerAuth(token);
  }

  private long chunkCount(long size, int chunkSize) {
    return (size + chunkSize - 1) / chunkSize;
  }

  private static boolean isUploadUri(URI uri, URI apiBase, String apiVersion) {
    if (uri.getHost() == null || apiBase.getHost() == null) {
      return true;
    }
    String basePath = trimTrailingSlash(apiBase.getPath() == null ? "" : apiBase.getPath());
    String versionPath = basePath + "/" + trimSlashes(apiVersion);
    String requestPath = uri.getPath() == null ? "" : uri.getPath();
    if (requestPath.equals(versionPath) || requestPath.startsWith(versionPath + "/")) {
      return false;
    }
    return true;
  }

  private static boolean isSafeIdentifier(String value) {
    return value != null && value.matches("[A-Za-z0-9._~-]{1,200}");
  }

  private static void requireHttpsEndpoint(String value, String fieldName) {
    try {
      URI uri = URI.create(value);
      if (!"https".equalsIgnoreCase(uri.getScheme())
          || uri.getHost() == null
          || uri.getRawUserInfo() != null
          || uri.getRawQuery() != null
          || uri.getRawFragment() != null) {
        throw new IllegalArgumentException(
            fieldName + " must be an HTTPS origin without credentials");
      }
    } catch (RuntimeException failure) {
      if (failure instanceof IllegalArgumentException illegalArgumentException) {
        throw illegalArgumentException;
      }
      throw new IllegalArgumentException(fieldName + " must be a valid HTTPS endpoint", failure);
    }
  }

  private static void requireHttpsUploadUrl(String value) {
    try {
      URI uri = URI.create(value);
      if (!"https".equalsIgnoreCase(uri.getScheme())
          || uri.getHost() == null
          || uri.getRawUserInfo() != null) {
        throw new IllegalArgumentException("TikTok upload URL must be HTTPS without credentials");
      }
    } catch (RuntimeException failure) {
      if (failure instanceof IllegalArgumentException illegalArgumentException) {
        throw illegalArgumentException;
      }
      throw new IllegalArgumentException("TikTok upload URL is invalid", failure);
    }
  }

  private static String trimTrailingSlash(String value) {
    return value.replaceAll("/+$", "");
  }

  private static String trimSlashes(String value) {
    return value.replaceAll("^/+|/+$", "");
  }

  private static long deadlineNanos(Duration timeout) {
    try {
      return Math.addExact(System.nanoTime(), timeout.toNanos());
    } catch (ArithmeticException failure) {
      return Long.MAX_VALUE;
    }
  }

  private static boolean deadlineExceeded(long deadlineNanos) {
    return deadlineNanos != Long.MAX_VALUE && System.nanoTime() >= deadlineNanos;
  }

  private static Duration remaining(long deadlineNanos) {
    if (deadlineNanos == Long.MAX_VALUE) {
      return Duration.ofNanos(Long.MAX_VALUE);
    }
    long remaining = deadlineNanos - System.nanoTime();
    return remaining <= 0 ? Duration.ZERO : Duration.ofNanos(remaining);
  }

  private static Duration bounded(Duration value, Duration maximum) {
    Duration normalized = value == null || value.isNegative() ? Duration.ZERO : value;
    return normalized.compareTo(maximum) > 0 ? maximum : normalized;
  }

  private static Duration positive(Duration value, Duration fallback) {
    return value == null || value.isZero() || value.isNegative() ? fallback : value;
  }

  private static String text(JsonNode node, String field) {
    if (node == null || node.isMissingNode() || node.get(field) == null) {
      return null;
    }
    return node.get(field).asText(null);
  }

  private static String nonBlank(String value) {
    return value == null || value.isBlank() ? null : value;
  }

  private static String nonBlank(String value, String fallback) {
    return value == null || value.isBlank() ? fallback : value;
  }

  private static String firstNonBlank(String... values) {
    for (String value : values) {
      if (value != null && !value.isBlank()) {
        return value;
      }
    }
    return null;
  }

  private void sleep(Duration duration) {
    if (duration == null || duration.isZero() || duration.isNegative()) {
      return;
    }
    try {
      Thread.sleep(duration.toMillis());
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new TikTokProviderException(
          "TikTok provider operation was interrupted",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true),
          failure);
    }
  }

  private record Asset(Path path, long size) {}

  private record InitResponse(String publishId, String uploadUrl, String providerRequestId) {}

  private record ProviderResponse(JsonNode body, String providerRequestId, int status) {}

  public static class TikTokValidationException extends RuntimeException {
    public TikTokValidationException(String message) {
      super(message);
    }
  }

  public static class TikTokProviderException extends RuntimeException {
    private final String providerRequestId;
    private final ProviderErrorMapper.Classification classification;

    public TikTokProviderException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification) {
      super(message);
      this.providerRequestId = providerRequestId;
      this.classification = classification;
    }

    public TikTokProviderException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification,
        Throwable cause) {
      super(message, cause);
      this.providerRequestId = providerRequestId;
      this.classification = classification;
    }

    public String providerRequestId() {
      return providerRequestId;
    }

    public ProviderErrorMapper.Classification classification() {
      return classification;
    }
  }
}
