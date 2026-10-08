package com.pompom.youtubepublisher.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.MissingNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishersupport.ProviderErrorMapper;
import com.pompom.publishersupport.SecretRedactor;
import com.pompom.youtubepublisher.YouTubePublisherProperties;
import com.pompom.youtubepublisher.oauth.YouTubeCredentialService;
import com.pompom.youtubepublisher.oauth.YouTubeCredentialService.YouTubeCredentialException;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;
import java.util.function.Consumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.StreamUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

/** YouTube Data API resumable-upload adapter with conservative uncertainty handling. */
@Component
public class YouTubeDataClient {

  public static final int TITLE_LIMIT = 100;
  public static final int DESCRIPTION_LIMIT = 5000;
  public static final int TAGS_LIMIT = 500;
  public static final String VIDEO_CONTENT_TYPE = "video/*";

  private static final String SAFE_IDENTIFIER_PATTERN = "^[A-Za-z0-9._~-]{1,200}$";
  private static final Pattern RANGE_HEADER_PATTERN = Pattern.compile("^bytes=(\\d+)-(\\d+)$");
  private static final Pattern SHORTS_TOKEN_PATTERN =
      Pattern.compile(
          "(?<![\\p{L}\\p{N}_])#shorts(?![\\p{L}\\p{N}_])",
          Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);
  private static final String INIT_SUFFIX = "/videos?uploadType=resumable&part=snippet,status";
  private static final String RECONCILE_SUFFIX = "/videos?part=id,status&id=";

  private final RestClient restClient;
  private final ObjectMapper objectMapper;
  private final YouTubePublisherProperties properties;
  private final YouTubeCredentialService credentials;
  private final ProviderErrorMapper errorMapper = new ProviderErrorMapper();
  private final SecretRedactor redactor = new SecretRedactor();

  @Autowired
  public YouTubeDataClient(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      YouTubePublisherProperties properties,
      YouTubeCredentialService credentials) {
    this(builder.build(), objectMapper, properties, credentials);
  }

  public YouTubeDataClient(
      RestClient.Builder builder,
      ObjectMapper objectMapper,
      YouTubePublisherProperties properties) {
    this(
        builder.build(),
        objectMapper,
        properties,
        new YouTubeCredentialService(builder, objectMapper, properties));
  }

  public YouTubeDataClient(
      RestClient restClient,
      ObjectMapper objectMapper,
      YouTubePublisherProperties properties,
      YouTubeCredentialService credentials) {
    this.restClient = Objects.requireNonNull(restClient, "restClient");
    this.objectMapper = Objects.requireNonNull(objectMapper, "objectMapper");
    this.properties = Objects.requireNonNull(properties, "properties");
    this.credentials = Objects.requireNonNull(credentials, "credentials");
    requireHttpsEndpoint("apiBaseUrl", properties.apiBaseUrl());
    requireHttpsEndpoint("uploadBaseUrl", properties.uploadBaseUrl());
  }

  /** Creates separate bounded API and upload request factories. */
  public static ClientHttpRequestFactory deadlineRequestFactory(
      YouTubePublisherProperties properties) {
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
    URI uploadBase = URI.create(properties.uploadBaseUrl());
    return (uri, method) ->
        method == HttpMethod.PUT || isUploadUri(uri, uploadBase)
            ? uploadFactory.createRequest(uri, method)
            : apiFactory.createRequest(uri, method);
  }

  public PublishResult publish(PublishCommand command) {
    String providerRequestId = null;
    try {
      Asset asset = validateAsset(command);
      Metadata metadata = metadata(command);
      String accessToken = credentials.accessToken();
      InitResponse init = initialize(asset, metadata, accessToken);
      providerRequestId = init.providerRequestId();
      String videoId = upload(asset, init.uploadUrl());
      return completed(videoId, providerRequestId);
    } catch (YouTubeValidationException failure) {
      return failed(PublishErrorClass.VALIDATION, failure.getMessage(), providerRequestId);
    } catch (YouTubeCredentialException failure) {
      return mapCredentialFailure(failure, providerRequestId);
    } catch (YouTubeProviderException failure) {
      return mapProviderFailure(failure, providerRequestId);
    } catch (IOException failure) {
      return reconciliationRequired(
          null,
          providerRequestId,
          redactor.redact(
              "YouTube upload could not read the asset: " + failure.getMessage(),
              properties.accessToken(),
              properties.refreshToken()));
    } catch (RuntimeException failure) {
      return reconciliationRequired(
          null,
          providerRequestId,
          redactor.redact(
              "YouTube provider operation was uncertain: " + failure.getMessage(),
              properties.accessToken(),
              properties.refreshToken(),
              properties.clientSecret()));
    }
  }

  /** Performs only a read-only status lookup for a known provider video identity. */
  public PublishResult reconcile(String providerVideoId) {
    if (!isSafeIdentifier(providerVideoId)) {
      return reconciliationRequired(
          providerVideoId, null, "YouTube provider video identity is invalid");
    }
    try {
      String accessToken = credentials.accessToken();
      ProviderResponse response =
          getJson(apiBase() + RECONCILE_SUFFIX + providerVideoId, accessToken);
      JsonNode items = response.body().path("items");
      if (!items.isArray() || items.size() != 1) {
        return reconciliationRequired(
            providerVideoId,
            response.providerRequestId(),
            "YouTube reconciliation returned ambiguous video evidence");
      }
      JsonNode item = items.get(0);
      String returnedId = text(item, "id");
      if (!providerVideoId.equals(returnedId)) {
        return reconciliationRequired(
            providerVideoId,
            response.providerRequestId(),
            "YouTube reconciliation identity did not match the requested video");
      }
      String uploadStatus = text(item.path("status"), "uploadStatus");
      if ("processed".equalsIgnoreCase(uploadStatus)) {
        return completed(providerVideoId, response.providerRequestId());
      }
      if ("failed".equalsIgnoreCase(uploadStatus)
          || "rejected".equalsIgnoreCase(uploadStatus)
          || "deleted".equalsIgnoreCase(uploadStatus)) {
        String reason =
            firstNonBlank(
                text(item.path("status"), "failureReason"),
                text(item.path("status"), "rejectionReason"),
                "YouTube rejected the video");
        return failed(
            PublishErrorClass.PROVIDER_REJECTED,
            redactor.redact(reason, properties.accessToken(), properties.refreshToken()),
            response.providerRequestId(),
            providerVideoId);
      }
      return reconciliationRequired(
          providerVideoId,
          response.providerRequestId(),
          "YouTube video status is not final: " + safeStatus(uploadStatus));
    } catch (YouTubeCredentialException failure) {
      return reconciliationRequired(
          providerVideoId,
          failure.providerRequestId(),
          redactor.redact(
              failure.getMessage(), properties.accessToken(), properties.refreshToken()));
    } catch (YouTubeProviderException failure) {
      return reconciliationRequired(
          providerVideoId,
          failure.providerRequestId(),
          redactor.redact(
              failure.getMessage(), properties.accessToken(), properties.refreshToken()));
    } catch (RuntimeException failure) {
      return reconciliationRequired(
          providerVideoId,
          null,
          redactor.redact(
              "YouTube reconciliation failed: " + failure.getMessage(),
              properties.accessToken(),
              properties.refreshToken()));
    }
  }

  private InitResponse initialize(Asset asset, Metadata metadata, String accessToken)
      throws YouTubeProviderException {
    ProviderResponse response =
        postJson(
            uploadApi() + INIT_SUFFIX,
            metadata.body(),
            accessToken,
            "YouTube upload initialization",
            headers -> {
              headers.set("X-Upload-Content-Type", VIDEO_CONTENT_TYPE);
              headers.set("X-Upload-Content-Length", Long.toString(asset.size()));
            });
    String location = response.location();
    if (location == null || location.isBlank()) {
      throw new YouTubeProviderException(
          "YouTube upload initialization returned no safe upload URL",
          response.providerRequestId(),
          new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true));
    }
    requireSafeUploadUrl(location);
    return new InitResponse(location, response.providerRequestId());
  }

  private String upload(Asset asset, String uploadUrl)
      throws IOException, YouTubeProviderException {
    long uploaded = 0;
    try (SeekableByteChannel input = Files.newByteChannel(asset.path())) {
      while (uploaded < asset.size()) {
        int requested = (int) Math.min(properties.chunkSize(), asset.size() - uploaded);
        byte[] chunk = readChunk(input, uploaded, requested);
        long start = uploaded;
        long end = uploaded + chunk.length - 1;
        ProviderResponse response =
            putUpload(
                uploadUrl,
                chunk,
                "bytes " + start + "-" + end + "/" + asset.size(),
                "YouTube video chunk upload");
        int status = response.status();
        if (status == 308) {
          uploaded = acknowledgedOffset(response, start, end, asset.size());
          continue;
        }
        if (status < 200 || status >= 300) {
          throw providerFailure(response, "YouTube video chunk upload");
        }
        uploaded += chunk.length;
        if (uploaded >= asset.size()) {
          String videoId = text(response.body(), "id");
          if (!isSafeIdentifier(videoId)) {
            throw new YouTubeProviderException(
                "YouTube final upload response contained no safe video identity",
                response.providerRequestId(),
                new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true));
          }
          return videoId;
        }
      }
    }
    throw new YouTubeProviderException(
        "YouTube upload ended without a provider video identity",
        null,
        new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true));
  }

  private byte[] readChunk(SeekableByteChannel input, long offset, int requested)
      throws IOException, YouTubeProviderException {
    input.position(offset);
    ByteBuffer buffer = ByteBuffer.allocate(requested);
    while (buffer.hasRemaining()) {
      int read = input.read(buffer);
      if (read < 0) {
        break;
      }
      if (read == 0) {
        break;
      }
    }
    if (buffer.position() != requested) {
      throw new YouTubeProviderException(
          "YouTube asset changed while it was being uploaded",
          null,
          new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true));
    }
    return buffer.array();
  }

  private long acknowledgedOffset(ProviderResponse response, long start, long end, long assetSize) {
    String range = response.range();
    if (range == null || range.isBlank()) {
      throw invalidAcknowledgement("YouTube upload acknowledgement did not include a Range");
    }
    Matcher matcher = RANGE_HEADER_PATTERN.matcher(range.trim());
    if (!matcher.matches()) {
      throw invalidAcknowledgement("YouTube upload acknowledgement Range is invalid");
    }
    try {
      long acknowledgedStart = Long.parseLong(matcher.group(1));
      long acknowledgedEnd = Long.parseLong(matcher.group(2));
      if (acknowledgedStart != 0
          || acknowledgedEnd < acknowledgedStart
          || acknowledgedEnd > end
          || acknowledgedEnd >= assetSize
          || acknowledgedEnd + 1 <= start) {
        throw invalidAcknowledgement("YouTube upload acknowledgement Range is out of bounds");
      }
      return acknowledgedEnd + 1;
    } catch (NumberFormatException failure) {
      throw invalidAcknowledgement("YouTube upload acknowledgement Range is invalid");
    }
  }

  private YouTubeProviderException invalidAcknowledgement(String message) {
    return new YouTubeProviderException(
        message,
        null,
        new ProviderErrorMapper.Classification(PublishErrorClass.UNKNOWN, false, true));
  }

  private ProviderResponse postJson(String url, JsonNode body, String accessToken, String operation)
      throws YouTubeProviderException {
    return postJson(url, body, accessToken, operation, headers -> {});
  }

  private ProviderResponse postJson(
      String url,
      JsonNode body,
      String accessToken,
      String operation,
      Consumer<HttpHeaders> additionalHeaders)
      throws YouTubeProviderException {
    try {
      return restClient
          .post()
          .uri(URI.create(url))
          .headers(
              headers -> {
                applyJsonHeaders(headers, accessToken);
                additionalHeaders.accept(headers);
              })
          .body(body.toString())
          .exchange((request, response) -> parseResponse(request, response, operation));
    } catch (YouTubeProviderException failure) {
      throw failure;
    } catch (RestClientException failure) {
      throw transportFailure(operation, failure);
    }
  }

  private ProviderResponse getJson(String url, String accessToken) throws YouTubeProviderException {
    try {
      return restClient
          .get()
          .uri(URI.create(url))
          .headers(headers -> headers.setBearerAuth(accessToken))
          .exchange(
              (request, response) -> parseResponse(request, response, "YouTube reconciliation"));
    } catch (YouTubeProviderException failure) {
      throw failure;
    } catch (RestClientException failure) {
      throw transportFailure("YouTube reconciliation", failure);
    }
  }

  private ProviderResponse putUpload(String url, byte[] body, String contentRange, String operation)
      throws YouTubeProviderException {
    try {
      return restClient
          .put()
          .uri(URI.create(url))
          .headers(
              headers -> {
                headers.set(HttpHeaders.CONTENT_TYPE, VIDEO_CONTENT_TYPE);
                headers.set(HttpHeaders.CONTENT_RANGE, contentRange);
              })
          .body(body)
          .exchange((request, response) -> parseResponse(request, response, operation));
    } catch (YouTubeProviderException failure) {
      throw failure;
    } catch (RestClientException failure) {
      throw transportFailure(operation, failure);
    }
  }

  private ProviderResponse parseResponse(
      org.springframework.http.HttpRequest request, ClientHttpResponse response, String operation) {
    int status;
    String raw;
    try {
      status = response.getStatusCode().value();
      var body = response.getBody();
      raw = body == null ? "" : StreamUtils.copyToString(body, StandardCharsets.UTF_8);
    } catch (IOException failure) {
      throw new YouTubeProviderException(
          redactor.redact(
              operation + " response could not be read: " + failure.getMessage(),
              properties.accessToken(),
              properties.refreshToken()),
          providerRequestId(response.getHeaders()),
          errorMapper.classify(failure),
          failure);
    }
    JsonNode body = parseBody(raw);
    ProviderResponse parsed =
        new ProviderResponse(
            status,
            body,
            response.getHeaders().getFirst(HttpHeaders.LOCATION),
            response.getHeaders().getFirst(HttpHeaders.RANGE),
            providerRequestId(response.getHeaders(), body),
            raw);
    if (status >= 400 && status != 308) {
      throw providerFailure(parsed, operation);
    }
    return parsed;
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

  private YouTubeProviderException providerFailure(ProviderResponse response, String operation) {
    String code =
        firstNonBlank(
            text(response.body().path("error"), "reason"),
            text(response.body().path("error"), "status"),
            text(response.body().path("error"), "code"),
            firstErrorReason(response.body()));
    ProviderErrorMapper.Classification classification =
        errorMapper.classify(response.status(), code);
    if (response.status() >= 500) {
      classification =
          new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true);
    }
    String message =
        firstNonBlank(
            text(response.body().path("error"), "message"),
            "YouTube " + operation + " failed (HTTP " + response.status() + ")");
    return new YouTubeProviderException(
        redactor.redact(
            message,
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret()),
        response.providerRequestId(),
        classification);
  }

  private YouTubeProviderException transportFailure(String operation, RuntimeException failure) {
    ProviderErrorMapper.Classification classification = errorMapper.classify(failure);
    return new YouTubeProviderException(
        redactor.redact(
            operation + " failed: " + failure.getMessage(),
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret()),
        null,
        classification,
        failure);
  }

  private Asset validateAsset(PublishCommand command) {
    if (command == null) {
      throw new YouTubeValidationException("YouTube publish command is required");
    }
    if (command.assetReference() == null || command.assetReference().isBlank()) {
      throw new YouTubeValidationException("YouTube video file is required");
    }
    Path path;
    try {
      path = Path.of(command.assetReference());
    } catch (RuntimeException failure) {
      throw new YouTubeValidationException("YouTube video file path is invalid");
    }
    if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
      throw new YouTubeValidationException("YouTube video file is not available");
    }
    try {
      long size = Files.size(path);
      if (size <= 0) {
        throw new YouTubeValidationException("YouTube video file must not be empty");
      }
      if (size > properties.maxFileSize()) {
        throw new YouTubeValidationException(
            "YouTube video file exceeds the maximum size of "
                + properties.maxFileSize()
                + " bytes");
      }
      return new Asset(path, size);
    } catch (IOException failure) {
      throw new YouTubeValidationException("YouTube video file cannot be read");
    }
  }

  private Metadata metadata(PublishCommand command) {
    String title = command.title();
    if (title == null || title.isBlank()) {
      throw new YouTubeValidationException("YouTube title is required");
    }
    title = truncateCodePoints(title, TITLE_LIMIT);

    String description = command.caption() == null ? "" : command.caption();
    if (!containsShorts(description)) {
      description = description.isEmpty() ? "#Shorts" : description + "\n\n#Shorts";
    }
    if (description.codePointCount(0, description.length()) > DESCRIPTION_LIMIT) {
      throw new YouTubeValidationException(
          "YouTube description exceeds " + DESCRIPTION_LIMIT + " code points");
    }

    ObjectNode body = objectMapper.createObjectNode();
    ObjectNode snippet = body.putObject("snippet");
    snippet.put("title", title);
    snippet.put("description", description);
    ArrayNode tags = snippet.putArray("tags");
    List<String> normalizedTags = tags(command);
    int tagLength = 0;
    for (String tag : normalizedTags) {
      tagLength += tag.codePointCount(0, tag.length());
      tags.add(tag);
    }
    if (tagLength > TAGS_LIMIT) {
      throw new YouTubeValidationException("YouTube tags exceed " + TAGS_LIMIT + " code points");
    }

    String category =
        firstNonBlank(command.providerOptions().get("category_id"), properties.defaultCategoryId());
    if (category == null || !category.matches("^[0-9]{1,10}$")) {
      throw new YouTubeValidationException("YouTube category_id must be numeric");
    }
    snippet.put("categoryId", category);
    String defaultLanguage = command.providerOptions().get("default_language");
    if (defaultLanguage != null && !defaultLanguage.isBlank()) {
      if (!defaultLanguage.matches("^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{2,8})?$")) {
        throw new YouTubeValidationException("YouTube default_language is invalid");
      }
      snippet.put("defaultLanguage", defaultLanguage);
    }

    String privacy = privacyStatus(command);
    ObjectNode status = body.putObject("status");
    status.put("privacyStatus", privacy);
    String madeForKids = command.providerOptions().get("made_for_kids");
    if (madeForKids != null && !madeForKids.isBlank()) {
      if (!"true".equalsIgnoreCase(madeForKids) && !"false".equalsIgnoreCase(madeForKids)) {
        throw new YouTubeValidationException("YouTube made_for_kids must be true or false");
      }
      status.put("selfDeclaredMadeForKids", Boolean.parseBoolean(madeForKids));
    }
    return new Metadata(body);
  }

  private String privacyStatus(PublishCommand command) {
    List<String> explicit = new ArrayList<>();
    for (String key : List.of("privacy_level", "privacy_status", "privacy")) {
      String value = command.providerOptions().get(key);
      if (value != null && !value.isBlank()) {
        String normalized = value.trim().toLowerCase(Locale.ROOT);
        if (!explicit.contains(normalized)) {
          explicit.add(normalized);
        }
      }
    }
    if (explicit.size() > 1) {
      throw new YouTubeValidationException("YouTube privacy options conflict");
    }
    String privacy =
        explicit.isEmpty()
            ? (command.isPrivate() ? "private" : properties.defaultPrivacyStatus())
            : explicit.get(0);
    privacy = privacy == null ? null : privacy.trim().toLowerCase(Locale.ROOT);
    if (!Set.of("public", "unlisted", "private").contains(privacy)) {
      throw new YouTubeValidationException("YouTube privacy status is invalid");
    }
    if (command.isPrivate() && !"private".equals(privacy)) {
      throw new YouTubeValidationException(
          "YouTube isPrivate=true conflicts with public or unlisted privacy");
    }
    return privacy;
  }

  private List<String> tags(PublishCommand command) {
    List<String> values = new ArrayList<>();
    for (String hashtag : command.hashtags()) {
      if (hashtag != null && !hashtag.isBlank()) {
        values.add(hashtag.trim());
      }
    }
    String optionTags = command.providerOptions().get("tags");
    if (optionTags != null && !optionTags.isBlank()) {
      for (String tag : optionTags.split(",")) {
        if (!tag.isBlank()) {
          values.add(tag.trim());
        }
      }
    }
    return List.copyOf(values);
  }

  private PublishResult mapCredentialFailure(
      YouTubeCredentialException failure, String providerRequestId) {
    String requestId = firstNonBlank(failure.providerRequestId(), providerRequestId);
    ProviderErrorMapper.Classification classification = failure.classification();
    String message =
        redactor.redact(
            failure.getMessage(),
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret());
    if (classification.uncertainAfterSubmission()
        || classification.errorClass() == PublishErrorClass.TRANSIENT
        || classification.errorClass() == PublishErrorClass.UNKNOWN) {
      return reconciliationRequired(null, requestId, message);
    }
    return failed(classification.errorClass(), message, requestId);
  }

  private PublishResult mapProviderFailure(
      YouTubeProviderException failure, String providerRequestId) {
    String requestId = firstNonBlank(failure.providerRequestId(), providerRequestId);
    String message =
        redactor.redact(
            failure.getMessage(),
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret());
    if (failure.classification().uncertainAfterSubmission()
        || failure.classification().errorClass() == PublishErrorClass.TRANSIENT
        || failure.classification().errorClass() == PublishErrorClass.UNKNOWN) {
      return reconciliationRequired(null, requestId, message);
    }
    return failed(failure.classification().errorClass(), message, requestId);
  }

  private PublishResult completed(String videoId, String providerRequestId) {
    return new PublishResult(
        PublishStatus.COMPLETED,
        null,
        videoId,
        "https://youtube.com/shorts/" + videoId,
        providerRequestId,
        null,
        null,
        false);
  }

  private PublishResult failed(
      PublishErrorClass errorClass, String message, String providerRequestId) {
    return failed(errorClass, message, providerRequestId, null);
  }

  private PublishResult failed(
      PublishErrorClass errorClass,
      String message,
      String providerRequestId,
      String providerVideoId) {
    PublishErrorClass normalized =
        errorClass == null
                || errorClass == PublishErrorClass.TRANSIENT
                || errorClass == PublishErrorClass.UNKNOWN
                || errorClass == PublishErrorClass.RECONCILIATION_REQUIRED
            ? PublishErrorClass.PROVIDER_REJECTED
            : errorClass;
    return new PublishResult(
        PublishStatus.FAILED,
        null,
        providerVideoId,
        null,
        providerRequestId,
        normalized.wireValue(),
        redactor.redact(
            message,
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret()),
        false);
  }

  private PublishResult reconciliationRequired(
      String providerVideoId, String providerRequestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        null,
        providerVideoId,
        null,
        providerRequestId,
        PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
        redactor.redact(
            message,
            properties.accessToken(),
            properties.refreshToken(),
            properties.clientSecret()),
        true);
  }

  private String apiBase() {
    return trimTrailingSlash(properties.apiBaseUrl());
  }

  private String uploadApi() {
    return trimTrailingSlash(properties.uploadBaseUrl());
  }

  private void applyJsonHeaders(HttpHeaders headers, String accessToken) {
    headers.setBearerAuth(accessToken);
    headers.setContentType(MediaType.APPLICATION_JSON);
    headers.setAccept(List.of(MediaType.APPLICATION_JSON));
  }

  private static boolean containsShorts(String value) {
    return value != null && SHORTS_TOKEN_PATTERN.matcher(value).find();
  }

  private static String truncateCodePoints(String value, int limit) {
    if (value.codePointCount(0, value.length()) <= limit) {
      return value;
    }
    return value.substring(0, value.offsetByCodePoints(0, limit - 3)) + "...";
  }

  private static String text(JsonNode node, String field) {
    if (node == null || !node.isObject()) {
      return null;
    }
    JsonNode value = node.get(field);
    return value == null || value.isNull() || !value.isValueNode() ? null : value.asText();
  }

  private static String firstErrorReason(JsonNode body) {
    JsonNode errors = body.path("error").path("errors");
    if (!errors.isArray() || errors.isEmpty()) {
      return null;
    }
    return text(errors.get(0), "reason");
  }

  private static String firstNonBlank(String... values) {
    for (String value : values) {
      if (value != null && !value.isBlank()) {
        return value;
      }
    }
    return null;
  }

  private static String safeStatus(String value) {
    return value == null || value.isBlank() ? "unknown" : value.replaceAll("[^A-Za-z0-9_.-]", "");
  }

  private static boolean isSafeIdentifier(String value) {
    return value != null && value.matches(SAFE_IDENTIFIER_PATTERN);
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

  private static void requireSafeUploadUrl(String value) {
    URI upload = URI.create(value);
    if (!"https".equalsIgnoreCase(upload.getScheme())
        || upload.getHost() == null
        || upload.getUserInfo() != null
        || containsCredentialQuery(upload.getRawQuery())) {
      throw new YouTubeValidationException("YouTube upload URL is not safe");
    }
  }

  private static boolean containsCredentialQuery(String query) {
    if (query == null) {
      return false;
    }
    String normalized = query.toLowerCase(Locale.ROOT);
    return normalized.contains("access_token")
        || normalized.contains("refresh_token")
        || normalized.contains("client_secret")
        || normalized.contains("authorization")
        || normalized.contains("bearer");
  }

  private static boolean isUploadUri(URI uri, URI uploadBase) {
    return uri.getHost() != null
        && uploadBase.getHost() != null
        && (uri.getHost().equalsIgnoreCase(uploadBase.getHost())
            || uri.getPath().startsWith(trimTrailingSlash(uploadBase.getPath())));
  }

  private static String trimTrailingSlash(String value) {
    return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
  }

  private static Duration positive(Duration value, Duration fallback) {
    return value == null || value.isZero() || value.isNegative() ? fallback : value;
  }

  private record Asset(Path path, long size) {}

  private record Metadata(ObjectNode body) {}

  private record InitResponse(String uploadUrl, String providerRequestId) {}

  private record ProviderResponse(
      int status,
      JsonNode body,
      String location,
      String range,
      String providerRequestId,
      String rawBody) {}

  private static class YouTubeValidationException extends IllegalArgumentException {
    YouTubeValidationException(String message) {
      super(message);
    }
  }

  private static class YouTubeProviderException extends RuntimeException {
    private final String providerRequestId;
    private final ProviderErrorMapper.Classification classification;

    YouTubeProviderException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification) {
      this(message, providerRequestId, classification, null);
    }

    YouTubeProviderException(
        String message,
        String providerRequestId,
        ProviderErrorMapper.Classification classification,
        Throwable cause) {
      super(message, cause);
      this.providerRequestId = providerRequestId;
      this.classification = Objects.requireNonNull(classification, "classification");
    }

    String providerRequestId() {
      return providerRequestId;
    }

    ProviderErrorMapper.Classification classification() {
      return classification;
    }
  }

  private static String providerRequestId(HttpHeaders headers) {
    return providerRequestId(headers, MissingNode.getInstance());
  }

  private static String providerRequestId(HttpHeaders headers, JsonNode body) {
    String value =
        firstNonBlank(
            headers.getFirst("x-goog-request-id"),
            headers.getFirst("x-youtube-request-id"),
            headers.getFirst("x-request-id"),
            text(body, "requestId"));
    return value != null && value.matches("^[A-Za-z0-9._~:-]{1,200}$") ? value : null;
  }
}
