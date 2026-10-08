package com.pompom.metapublisher;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.pompom.metapublisher.storage.PublicMediaStorage;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.RetryPolicy;
import com.pompom.publishersupport.SecretRedactor;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.util.UriUtils;

public final class MetaClientSupport {

  private static final Pattern SAFE_PATH_SEGMENT = Pattern.compile("[A-Za-z0-9._~-]{1,200}");

  private static final Set<String> AUTH_CODES =
      Set.of("102", "190", "200", "458", "459", "463", "464", "467");
  private static final Set<String> RATE_LIMIT_CODES = Set.of("4", "17", "32", "613");

  private final RestClient restClient;
  private final ObjectMapper objectMapper;
  private final ProviderErrorMapper errorMapper;
  private final SecretRedactor redactor;
  private final RetryPolicy retryPolicy;
  private final int maxAttempts;
  private final Duration requestTimeout;
  private final Duration uploadTimeout;

  public static String pathSegment(String fieldName, String value) {
    if (fieldName == null || fieldName.isBlank()) {
      throw new IllegalArgumentException("path field name is required");
    }
    if (value == null
        || ".".equals(value)
        || "..".equals(value)
        || !SAFE_PATH_SEGMENT.matcher(value).matches()) {
      throw new IllegalArgumentException(fieldName + " is not a safe provider identifier");
    }
    return UriUtils.encodePathSegment(value, StandardCharsets.UTF_8);
  }

  public static String requireHttpsEndpoint(String fieldName, String value) {
    if (fieldName == null || fieldName.isBlank()) {
      throw new IllegalArgumentException("endpoint field name is required");
    }
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
      canonicalPath(fieldName, uri);
      return trimTrailingSlash(value);
    } catch (RuntimeException failure) {
      if (failure instanceof IllegalArgumentException illegalArgumentException) {
        throw illegalArgumentException;
      }
      throw new IllegalArgumentException(fieldName + " must be a valid HTTPS endpoint", failure);
    }
  }

  public static String requireSafeUploadUrl(
      String fieldName, String value, String configuredBaseUrl) {
    String base = requireHttpsEndpoint("ruploadBaseUrl", configuredBaseUrl);
    if (!PublicMediaStorage.isSafeHttpsUrl(value)) {
      throw new IllegalArgumentException(fieldName + " is not a safe HTTPS upload URL");
    }
    try {
      URI baseUri = URI.create(base);
      URI uploadUri = URI.create(value);
      String basePath = canonicalPath("ruploadBaseUrl", baseUri);
      String uploadPath = canonicalPath(fieldName, uploadUri);
      if (!sameOrigin(baseUri, uploadUri)
          || !(uploadPath.equals(basePath) || uploadPath.startsWith(basePath + "/"))) {
        throw new IllegalArgumentException(fieldName + " is outside the configured upload origin");
      }
      return value;
    } catch (RuntimeException failure) {
      if (failure instanceof IllegalArgumentException illegalArgumentException) {
        throw illegalArgumentException;
      }
      throw new IllegalArgumentException(fieldName + " is not a valid upload URL", failure);
    }
  }

  private static String canonicalPath(String fieldName, URI uri) {
    String path = uri.getPath() == null ? "" : uri.getPath();
    for (String segment : path.split("/", -1)) {
      if (".".equals(segment) || "..".equals(segment)) {
        throw new IllegalArgumentException(fieldName + " must not contain dot-segment traversal");
      }
    }
    String normalized = uri.normalize().getPath();
    return normalized == null ? "" : normalized;
  }

  private static boolean sameOrigin(URI first, URI second) {
    return first.getScheme().equalsIgnoreCase(second.getScheme())
        && first.getHost().equalsIgnoreCase(second.getHost())
        && first.getPort() == second.getPort();
  }

  public static ClientHttpRequestFactory deadlineRequestFactory(
      MetaPublisherProperties properties) {
    requireHttpsEndpoint(
        "graphBaseUrl",
        properties.graphBaseUrl() == null || properties.graphBaseUrl().isBlank()
            ? "https://graph.facebook.com"
            : properties.graphBaseUrl());
    requireHttpsEndpoint(
        "ruploadBaseUrl",
        properties.ruploadBaseUrl() == null || properties.ruploadBaseUrl().isBlank()
            ? "https://rupload.facebook.com/video-upload"
            : properties.ruploadBaseUrl());
    Duration requestTimeout = positiveTimeout(properties.requestTimeout(), Duration.ofSeconds(120));
    Duration uploadTimeout = positiveTimeout(properties.uploadTimeout(), Duration.ofSeconds(600));
    JdkClientHttpRequestFactory graphFactory =
        new JdkClientHttpRequestFactory(
            HttpClient.newBuilder().connectTimeout(requestTimeout).build());
    graphFactory.setReadTimeout(requestTimeout);
    JdkClientHttpRequestFactory uploadFactory =
        new JdkClientHttpRequestFactory(
            HttpClient.newBuilder().connectTimeout(uploadTimeout).build());
    uploadFactory.setReadTimeout(uploadTimeout);
    return (uri, method) ->
        isUploadUri(uri)
            ? uploadFactory.createRequest(uri, method)
            : graphFactory.createRequest(uri, method);
  }

  private static String trimTrailingSlash(String value) {
    return value.replaceAll("/+$", "");
  }

  private static Duration positiveTimeout(Duration value, Duration fallback) {
    return value == null || value.isZero() || value.isNegative() ? fallback : value;
  }

  private static boolean isUploadUri(URI uri) {
    String host = uri.getHost() == null ? "" : uri.getHost().toLowerCase(Locale.ROOT);
    String path = uri.getPath() == null ? "" : uri.getPath().toLowerCase(Locale.ROOT);
    return host.contains("rupload") || path.contains("video-upload");
  }

  public MetaClientSupport(RestClient.Builder builder, ObjectMapper objectMapper, int maxAttempts) {
    this(builder, objectMapper, maxAttempts, Duration.ofSeconds(120), Duration.ofSeconds(600));
  }

  public MetaClientSupport(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      int maxAttempts,
      Duration requestTimeout,
      Duration uploadTimeout) {
    this(
        builder.build(),
        objectMapper,
        new ProviderErrorMapper(),
        new SecretRedactor(),
        maxAttempts,
        requestTimeout,
        uploadTimeout);
  }

  public MetaClientSupport(
      RestClient restClient,
      ObjectMapper objectMapper,
      ProviderErrorMapper errorMapper,
      SecretRedactor redactor,
      int maxAttempts) {
    this(
        restClient,
        objectMapper,
        errorMapper,
        redactor,
        maxAttempts,
        Duration.ofSeconds(120),
        Duration.ofSeconds(600));
  }

  public MetaClientSupport(
      RestClient restClient,
      ObjectMapper objectMapper,
      ProviderErrorMapper errorMapper,
      SecretRedactor redactor,
      int maxAttempts,
      Duration requestTimeout,
      Duration uploadTimeout) {
    this.restClient = restClient;
    this.objectMapper = objectMapper;
    this.errorMapper = errorMapper;
    this.redactor = redactor;
    this.maxAttempts = Math.max(1, maxAttempts);
    this.retryPolicy =
        new RetryPolicy(
            this.maxAttempts, RetryPolicy.DEFAULT_INITIAL_BACKOFF, RetryPolicy.DEFAULT_MAX_BACKOFF);
    this.requestTimeout = requestTimeout;
    this.uploadTimeout = uploadTimeout;
  }

  public MetaResponse postForm(
      String url,
      String token,
      Map<String, String> values,
      RetryPolicy.SubmissionPhase submissionPhase) {
    LinkedMultiValueMap<String, String> form = new LinkedMultiValueMap<>();
    values.forEach(form::add);
    return execute(
        () ->
            restClient
                .post()
                .uri(URI.create(url))
                .header(HttpHeaders.AUTHORIZATION, bearer(token))
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .body(form)
                .exchange((request, response) -> parseResponse(response, token)),
        submissionPhase,
        "POST " + url,
        requestTimeout);
  }

  public MetaResponse postUpload(
      String url,
      String token,
      byte[] body,
      Map<String, String> headers,
      RetryPolicy.SubmissionPhase submissionPhase) {
    return execute(
        () ->
            restClient
                .post()
                .uri(URI.create(url))
                .headers(
                    httpHeaders -> {
                      httpHeaders.set(HttpHeaders.AUTHORIZATION, "OAuth " + token);
                      headers.forEach(httpHeaders::set);
                    })
                .body(body)
                .exchange((request, response) -> parseResponse(response, token)),
        submissionPhase,
        "POST upload",
        uploadTimeout);
  }

  public MetaResponse get(String url, String token, RetryPolicy.SubmissionPhase submissionPhase) {
    return execute(
        () ->
            restClient
                .get()
                .uri(URI.create(url))
                .header(HttpHeaders.AUTHORIZATION, bearer(token))
                .exchange((request, response) -> parseResponse(response, token)),
        submissionPhase,
        "GET " + url,
        requestTimeout);
  }

  private MetaResponse execute(
      Supplier<MetaResponse> operation,
      RetryPolicy.SubmissionPhase submissionPhase,
      String operationName,
      Duration timeout) {
    MetaProviderException lastFailure = null;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return runWithTimeout(operation, timeout, operationName);
      } catch (MetaProviderException failure) {
        lastFailure = failure;
        RetryPolicy.Decision decision =
            retryPolicy.decide(failure.classification(), attempt, submissionPhase);
        if (!decision.shouldRetry() || attempt == maxAttempts) {
          throw failure;
        }
        sleep(decision.backoff(), operationName);
      } catch (RestClientException failure) {
        MetaProviderException mapped = transportFailure(failure, operationName);
        lastFailure = mapped;
        RetryPolicy.Decision decision =
            retryPolicy.decide(mapped.classification(), attempt, submissionPhase);
        if (!decision.shouldRetry() || attempt == maxAttempts) {
          throw mapped;
        }
        sleep(decision.backoff(), operationName);
      }
    }
    throw lastFailure == null
        ? new IllegalStateException("Meta operation ended without a result")
        : lastFailure;
  }

  private MetaResponse runWithTimeout(
      Supplier<MetaResponse> operation, Duration timeout, String operationName) {
    if (timeout == null || timeout.isZero() || timeout.isNegative()) {
      return operation.get();
    }
    ExecutorService executor =
        Executors.newSingleThreadExecutor(
            runnable -> {
              Thread thread = new Thread(runnable, "meta-provider-timeout");
              thread.setDaemon(true);
              return thread;
            });
    Future<MetaResponse> future = executor.submit(operation::get);
    try {
      return future.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
    } catch (TimeoutException failure) {
      future.cancel(true);
      throw new MetaProviderException(
          "Meta " + operationName + " timed out",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true),
          failure);
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new MetaProviderException(
          "Meta " + operationName + " was interrupted",
          null,
          errorMapper.classify(failure),
          failure);
    } catch (ExecutionException failure) {
      Throwable cause = failure.getCause();
      if (cause instanceof RuntimeException runtimeException) {
        throw runtimeException;
      }
      throw new RestClientException("Meta " + operationName + " failed", cause);
    } finally {
      executor.shutdownNow();
    }
  }

  private MetaResponse parseResponse(ClientHttpResponse response, String token) {
    try {
      String raw =
          response.getBody() == null
              ? ""
              : StreamUtils.copyToString(response.getBody(), StandardCharsets.UTF_8);
      int status = response.getStatusCode().value();
      JsonNode body = parseBody(raw, status, token);
      String requestId =
          firstNonBlank(
              response.getHeaders().getFirst("x-fb-trace-id"),
              response.getHeaders().getFirst("x-fb-request-id"),
              text(body, "fbtrace_id"),
              text(body.path("error"), "fbtrace_id"));
      if (status >= 400) {
        throw responseFailure(status, body, raw, requestId, token);
      }
      return new MetaResponse(body, requestId);
    } catch (IOException failure) {
      throw new MetaProviderException(
          redactor.redact("Meta response could not be read: " + failure.getMessage(), token),
          null,
          errorMapper.classify(failure),
          failure);
    }
  }

  private JsonNode parseBody(String raw, int status, String token) throws IOException {
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
      throw new MetaProviderException(
          redactor.redact("Meta response was not valid JSON: " + failure.getMessage(), token),
          status,
          null,
          null,
          errorMapper.classify(status));
    }
  }

  private MetaProviderException responseFailure(
      int status, JsonNode body, String raw, String requestId, String token) {
    JsonNode error = body.path("error");
    String code = text(error, "code");
    ProviderErrorMapper.Classification classification = classify(status, code);
    String message = text(error, "message");
    if (message == null || message.isBlank()) {
      message = "Meta provider request failed (HTTP " + status + ")";
    }
    return new MetaProviderException(
        redactor.redact(message, token), status, code, requestId, classification);
  }

  private MetaProviderException transportFailure(RestClientException failure, String operation) {
    Throwable root = failure;
    while (root.getCause() != null && root.getCause() != root) {
      root = root.getCause();
    }
    ProviderErrorMapper.Classification classification = errorMapper.classify(root);
    return new MetaProviderException(
        redactor.redact("Meta " + operation + " failed: " + root.getMessage()),
        null,
        classification,
        failure);
  }

  private ProviderErrorMapper.Classification classify(int status, String code) {
    if (AUTH_CODES.contains(normalizeCode(code))) {
      return new ProviderErrorMapper.Classification(PublishErrorClass.AUTHENTICATION, false, false);
    }
    if (RATE_LIMIT_CODES.contains(normalizeCode(code))) {
      return new ProviderErrorMapper.Classification(PublishErrorClass.RATE_LIMITED, true, false);
    }
    return errorMapper.classify(status, code);
  }

  private String bearer(String token) {
    return "Bearer " + token;
  }

  private String normalizeCode(String code) {
    return code == null ? "" : code.toLowerCase(Locale.ROOT);
  }

  private String text(JsonNode node, String field) {
    if (node == null || node.isMissingNode() || node.get(field) == null) {
      return null;
    }
    return node.get(field).asText(null);
  }

  private String firstNonBlank(String... values) {
    for (String value : values) {
      if (value != null && !value.isBlank()) {
        return value;
      }
    }
    return null;
  }

  private void sleep(Duration duration, String operationName) {
    if (duration.isZero() || duration.isNegative()) {
      return;
    }
    try {
      Thread.sleep(duration.toMillis());
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
      throw new MetaProviderException(
          "Meta " + operationName + " retry was interrupted",
          null,
          errorMapper.classify(failure),
          failure);
    }
  }

  public record MetaResponse(JsonNode body, String providerRequestId) {}
}
