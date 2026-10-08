package com.pompom.youtubepublisher;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;

/** Service-owned YouTube credentials, endpoints, and bounded operation settings. */
@ConfigurationProperties(prefix = "pompom.youtube")
public record YouTubePublisherProperties(
    boolean writeEnabled,
    boolean publishEnabled,
    boolean dryRun,
    String internalToken,
    String clientId,
    String clientSecret,
    String accessToken,
    String refreshToken,
    String tokenUrl,
    String apiBaseUrl,
    String uploadBaseUrl,
    int chunkSize,
    long maxFileSize,
    Duration requestTimeout,
    Duration uploadTimeout,
    int maxAttempts,
    String defaultCategoryId,
    String defaultPrivacyStatus,
    Boolean defaultMadeForKids,
    String platformAccountId) {

  public static final int DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024;
  public static final long DEFAULT_MAX_FILE_SIZE = 512L * 1024 * 1024;
  public static final Duration DEFAULT_REQUEST_TIMEOUT = Duration.ofSeconds(120);
  public static final Duration DEFAULT_UPLOAD_TIMEOUT = Duration.ofSeconds(600);
  public static final int DEFAULT_MAX_ATTEMPTS = 5;

  @ConstructorBinding
  public YouTubePublisherProperties {
    internalToken = valueOrEmpty(internalToken);
    clientId = valueOrEmpty(clientId);
    clientSecret = valueOrEmpty(clientSecret);
    accessToken = valueOrEmpty(accessToken);
    refreshToken = valueOrEmpty(refreshToken);
    tokenUrl = defaultValue(tokenUrl, "https://oauth2.googleapis.com/token");
    apiBaseUrl = defaultValue(apiBaseUrl, "https://www.googleapis.com/youtube/v3");
    uploadBaseUrl = defaultValue(uploadBaseUrl, "https://www.googleapis.com/upload/youtube/v3");
    chunkSize = chunkSize > 0 ? chunkSize : DEFAULT_CHUNK_SIZE;
    maxFileSize =
        maxFileSize > 0 ? Math.min(maxFileSize, DEFAULT_MAX_FILE_SIZE) : DEFAULT_MAX_FILE_SIZE;
    requestTimeout = positive(requestTimeout, DEFAULT_REQUEST_TIMEOUT);
    uploadTimeout = positive(uploadTimeout, DEFAULT_UPLOAD_TIMEOUT);
    maxAttempts = maxAttempts > 0 ? maxAttempts : DEFAULT_MAX_ATTEMPTS;
    defaultCategoryId = defaultValue(defaultCategoryId, "22");
    defaultPrivacyStatus = defaultValue(defaultPrivacyStatus, "public");
    platformAccountId = valueOrEmpty(platformAccountId);
  }

  /** Convenient constructor for provider-client tests and non-Spring callers. */
  public YouTubePublisherProperties(
      boolean writeEnabled,
      boolean publishEnabled,
      String internalToken,
      String accessToken,
      String refreshToken,
      String tokenUrl,
      String apiBaseUrl,
      String uploadBaseUrl,
      int chunkSize,
      long maxFileSize,
      Duration requestTimeout,
      Duration uploadTimeout,
      int maxAttempts,
      String defaultCategoryId,
      String defaultPrivacyStatus,
      String platformAccountId) {
    this(
        writeEnabled,
        publishEnabled,
        false,
        internalToken,
        "",
        "",
        accessToken,
        refreshToken,
        tokenUrl,
        apiBaseUrl,
        uploadBaseUrl,
        chunkSize,
        maxFileSize,
        requestTimeout,
        uploadTimeout,
        maxAttempts,
        defaultCategoryId,
        defaultPrivacyStatus,
        null,
        platformAccountId);
  }

  public static YouTubePublisherProperties defaults(
      String accessToken, String apiBaseUrl, String uploadBaseUrl) {
    return new YouTubePublisherProperties(
        true,
        true,
        false,
        "",
        "",
        "",
        accessToken,
        "",
        "https://oauth2.googleapis.com/token",
        apiBaseUrl,
        uploadBaseUrl,
        DEFAULT_CHUNK_SIZE,
        DEFAULT_MAX_FILE_SIZE,
        DEFAULT_REQUEST_TIMEOUT,
        DEFAULT_UPLOAD_TIMEOUT,
        DEFAULT_MAX_ATTEMPTS,
        "22",
        "public",
        null,
        "");
  }

  public boolean hasCredentialConfiguration() {
    return !accessToken.isBlank() || hasRefreshCredentialConfiguration();
  }

  public boolean hasRefreshCredentialConfiguration() {
    return !clientId.isBlank() && !clientSecret.isBlank() && !refreshToken.isBlank();
  }

  private static String valueOrEmpty(String value) {
    return value == null ? "" : value;
  }

  private static String defaultValue(String value, String fallback) {
    return value == null || value.isBlank() ? fallback : value;
  }

  private static Duration positive(Duration value, Duration fallback) {
    return value == null || value.isZero() || value.isNegative() ? fallback : value;
  }
}
