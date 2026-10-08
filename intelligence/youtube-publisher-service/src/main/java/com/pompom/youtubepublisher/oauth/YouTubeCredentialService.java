package com.pompom.youtubepublisher.oauth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.SecretRedactor;
import com.pompom.youtubepublisher.YouTubePublisherProperties;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;

/** Owns YouTube OAuth refreshes; refresh tokens never cross the shared publish contract. */
@Component
public class YouTubeCredentialService {

  private final RestClient restClient;
  private final ObjectMapper objectMapper;
  private final YouTubePublisherProperties properties;
  private final ProviderErrorMapper errorMapper = new ProviderErrorMapper();
  private final SecretRedactor redactor = new SecretRedactor();
  private final AtomicReference<RefreshOutcome> lastOutcome =
      new AtomicReference<>(RefreshOutcome.notAttempted());

  private String cachedAccessToken;
  private Instant cachedAccessTokenExpiry;

  @Autowired
  public YouTubeCredentialService(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      YouTubePublisherProperties properties) {
    this(builder.build(), objectMapper, properties);
  }

  public YouTubeCredentialService(
      RestClient restClient, ObjectMapper objectMapper, YouTubePublisherProperties properties) {
    this.restClient = Objects.requireNonNull(restClient, "restClient");
    this.objectMapper = Objects.requireNonNull(objectMapper, "objectMapper");
    this.properties = Objects.requireNonNull(properties, "properties");
    requireHttpsEndpoint("tokenUrl", properties.tokenUrl());
  }

  /** Returns an active access token only to provider-client code inside this service. */
  public synchronized String accessToken() {
    Instant now = Instant.now();
    if (cachedAccessToken != null
        && (cachedAccessTokenExpiry == null
            || now.plusSeconds(30).isBefore(cachedAccessTokenExpiry))) {
      return cachedAccessToken;
    }

    if (!properties.accessToken().isBlank() && cachedAccessToken == null) {
      cachedAccessToken = properties.accessToken();
      cachedAccessTokenExpiry = null;
      return cachedAccessToken;
    }
    if (!properties.hasRefreshCredentialConfiguration()) {
      throw new YouTubeCredentialException(
          "YouTube credentials are not configured",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.AUTHENTICATION, false, false));
    }
    return refreshAccessToken();
  }

  /** Refreshes and caches the provider token without exposing it in the refresh outcome. */
  public synchronized String refreshAccessToken() {
    if (!properties.hasRefreshCredentialConfiguration()) {
      throw new YouTubeCredentialException(
          "YouTube OAuth refresh credentials are not configured",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.AUTHENTICATION, false, false));
    }

    try {
      TokenResponse response =
          restClient
              .post()
              .uri(URI.create(properties.tokenUrl()))
              .header(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
              .contentType(MediaType.APPLICATION_FORM_URLENCODED)
              .body(formBody())
              .exchange(this::parseResponse);
      if (response.status() < 200 || response.status() >= 300) {
        throw credentialFailure(response);
      }

      String token = text(response.body(), "access_token");
      if (token == null || token.isBlank()) {
        throw new YouTubeCredentialException(
            "YouTube OAuth refresh returned no access token",
            response.providerRequestId(),
            new ProviderErrorMapper.Classification(PublishErrorClass.AUTHENTICATION, false, false));
      }
      cachedAccessToken = token;
      long expiresIn = response.body().path("expires_in").asLong(0);
      cachedAccessTokenExpiry = expiresIn > 0 ? Instant.now().plusSeconds(expiresIn) : null;
      lastOutcome.set(RefreshOutcome.success(response.providerRequestId()));
      return token;
    } catch (YouTubeCredentialException failure) {
      lastOutcome.set(
          RefreshOutcome.failure(
              failure.providerRequestId(),
              failure.classification().errorClass(),
              redactor.redact(
                  failure.getMessage(), properties.clientSecret(), properties.refreshToken())));
      throw failure;
    } catch (RuntimeException failure) {
      ProviderErrorMapper.Classification classification = errorMapper.classify(failure);
      String message =
          redactor.redact(
              "YouTube OAuth refresh failed: " + failure.getMessage(),
              properties.clientSecret(),
              properties.refreshToken(),
              properties.accessToken());
      lastOutcome.set(RefreshOutcome.failure(null, classification.errorClass(), message));
      throw new YouTubeCredentialException(message, null, classification, failure);
    }
  }

  /** Returns redacted refresh state for diagnostics; it contains no credential material. */
  public RefreshOutcome lastRefreshOutcome() {
    return lastOutcome.get();
  }

  private String formBody() {
    return "client_id="
        + encode(properties.clientId())
        + "&client_secret="
        + encode(properties.clientSecret())
        + "&refresh_token="
        + encode(properties.refreshToken())
        + "&grant_type=refresh_token";
  }

  private TokenResponse parseResponse(
      org.springframework.http.HttpRequest request, ClientHttpResponse response) {
    int status;
    String raw;
    try {
      status = response.getStatusCode().value();
      var body = response.getBody();
      raw = body == null ? "" : StreamUtils.copyToString(body, StandardCharsets.UTF_8);
    } catch (IOException failure) {
      throw new YouTubeCredentialException(
          "YouTube OAuth response could not be read",
          providerRequestId(response.getHeaders()),
          errorMapper.classify(failure),
          failure);
    }
    JsonNode body = parseBody(raw);
    return new TokenResponse(status, body, providerRequestId(response.getHeaders(), body));
  }

  private YouTubeCredentialException credentialFailure(TokenResponse response) {
    String code =
        firstNonBlank(text(response.body(), "error"), text(response.body(), "error_code"));
    ProviderErrorMapper.Classification classification =
        errorMapper.classify(response.status(), code);
    if ("invalid_grant".equalsIgnoreCase(code)) {
      classification =
          new ProviderErrorMapper.Classification(PublishErrorClass.AUTHENTICATION, false, false);
    }
    String message =
        firstNonBlank(
            text(response.body(), "error_description"),
            text(response.body(), "error"),
            "YouTube OAuth refresh failed (HTTP " + response.status() + ")");
    return new YouTubeCredentialException(
        redactor.redact(message, properties.clientSecret(), properties.refreshToken()),
        response.providerRequestId(),
        classification);
  }

  private JsonNode parseBody(String raw) {
    if (raw == null || raw.isBlank()) {
      return MissingNode.getInstance();
    }
    try {
      JsonNode parsed = objectMapper.readTree(raw);
      return parsed == null ? MissingNode.getInstance() : parsed;
    } catch (IOException ignored) {
      return MissingNode.getInstance();
    }
  }

  private String providerRequestId(HttpHeaders headers) {
    return providerRequestId(headers, MissingNode.getInstance());
  }

  private String providerRequestId(HttpHeaders headers, JsonNode body) {
    String value =
        firstNonBlank(
            headers.getFirst("x-goog-request-id"),
            headers.getFirst("x-youtube-request-id"),
            headers.getFirst("x-request-id"),
            text(body, "requestId"));
    return value != null && value.matches("^[A-Za-z0-9._~:-]{1,200}$") ? value : null;
  }

  private static String text(JsonNode node, String field) {
    if (node == null || !node.isObject()) {
      return null;
    }
    JsonNode value = node.get(field);
    return value == null || value.isNull() || !value.isValueNode() ? null : value.asText();
  }

  private static String firstNonBlank(String... values) {
    for (String value : values) {
      if (value != null && !value.isBlank()) {
        return value;
      }
    }
    return null;
  }

  private static String encode(String value) {
    return URLEncoder.encode(value, StandardCharsets.UTF_8);
  }

  private static void requireHttpsEndpoint(String name, String value) {
    URI endpoint = URI.create(value);
    if (!"https".equalsIgnoreCase(endpoint.getScheme())
        || endpoint.getRawAuthority() == null
        || endpoint.getRawAuthority().isBlank()
        || endpoint.getUserInfo() != null) {
      throw new IllegalArgumentException(name + " must be an HTTPS endpoint without user info");
    }
  }

  public record RefreshOutcome(
      String status, String providerRequestId, String errorClass, String message) {
    static RefreshOutcome notAttempted() {
      return new RefreshOutcome("not_attempted", null, null, null);
    }

    static RefreshOutcome success(String providerRequestId) {
      return new RefreshOutcome("succeeded", providerRequestId, null, null);
    }

    static RefreshOutcome failure(
        String providerRequestId, PublishErrorClass errorClass, String message) {
      return new RefreshOutcome(
          "failed", providerRequestId, errorClass == null ? null : errorClass.wireValue(), message);
    }
  }

  private record TokenResponse(int status, JsonNode body, String providerRequestId) {}

  public static class YouTubeCredentialException extends RuntimeException {
    private final String providerRequestId;
    private final ProviderErrorMapper.Classification classification;

    public YouTubeCredentialException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification) {
      this(message, providerRequestId, classification, null);
    }

    public YouTubeCredentialException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification,
        Throwable cause) {
      super(message, cause);
      this.providerRequestId = providerRequestId;
      this.classification = Objects.requireNonNull(classification, "classification");
    }

    public String providerRequestId() {
      return providerRequestId;
    }

    public ProviderErrorMapper.Classification classification() {
      return classification;
    }
  }
}
