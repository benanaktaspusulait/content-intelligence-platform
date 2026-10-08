package com.pompom.metapublisher;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.RetryPolicy;
import com.pompom.publishersupport.SecretRedactor;
import java.io.IOException;
import java.net.URI;
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
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

public final class MetaClientSupport {

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

  public MetaClientSupport(RestClient.Builder builder, ObjectMapper objectMapper, int maxAttempts) {
    this(
        builder,
        objectMapper,
        maxAttempts,
        Duration.ofSeconds(120),
        Duration.ofSeconds(600));
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
          new ProviderErrorMapper.Classification(
              PublishErrorClass.TRANSIENT, true, true),
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
