package com.pompom.tiktokpublisher;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Service-owned TikTok credentials, provider endpoints, and bounded operation settings. */
@ConfigurationProperties(prefix = "pompom.tiktok")
public record TikTokPublisherProperties(
    boolean writeEnabled,
    boolean publishEnabled,
    String internalToken,
    String accessToken,
    String apiBaseUrl,
    String apiVersion,
    boolean dryRun,
    int chunkSize,
    long maxFileSize,
    Duration requestTimeout,
    Duration uploadTimeout,
    Duration pollTimeout,
    Duration pollInterval,
    int maxAttempts,
    boolean creatorValidationEnabled,
    String privacyLevel,
    boolean disableDuet,
    boolean disableComment,
    boolean disableStitch,
    long videoCoverTimestampMs,
    String platformAccountId) {

  public static final int DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024;
  public static final long DEFAULT_MAX_FILE_SIZE = 287L * 1024 * 1024;
  public static final Duration DEFAULT_REQUEST_TIMEOUT = Duration.ofSeconds(120);
  public static final Duration DEFAULT_UPLOAD_TIMEOUT = Duration.ofSeconds(600);
  public static final Duration DEFAULT_POLL_TIMEOUT = Duration.ofSeconds(300);
  public static final Duration DEFAULT_POLL_INTERVAL = Duration.ofSeconds(5);
  public static final int DEFAULT_MAX_ATTEMPTS = 5;

  public TikTokPublisherProperties {
    internalToken = valueOrEmpty(internalToken);
    accessToken = valueOrEmpty(accessToken);
    apiBaseUrl = defaultValue(apiBaseUrl, "https://open.tiktokapis.com");
    apiVersion = defaultValue(apiVersion, "v2");
    chunkSize = chunkSize > 0 ? chunkSize : DEFAULT_CHUNK_SIZE;
    maxFileSize = maxFileSize > 0 ? maxFileSize : DEFAULT_MAX_FILE_SIZE;
    requestTimeout = positive(requestTimeout, DEFAULT_REQUEST_TIMEOUT);
    uploadTimeout = positive(uploadTimeout, DEFAULT_UPLOAD_TIMEOUT);
    pollTimeout = nonNegative(pollTimeout, DEFAULT_POLL_TIMEOUT);
    pollInterval = nonNegative(pollInterval, DEFAULT_POLL_INTERVAL);
    maxAttempts = maxAttempts > 0 ? maxAttempts : DEFAULT_MAX_ATTEMPTS;
    privacyLevel = defaultValue(privacyLevel, "SELF_ONLY");
    platformAccountId = valueOrEmpty(platformAccountId);
  }

  public TikTokPublisherProperties(
      String accessToken,
      String apiBaseUrl,
      int chunkSize,
      long maxFileSize,
      Duration pollTimeout,
      Duration pollInterval) {
    this(
        true,
        true,
        "",
        accessToken,
        apiBaseUrl,
        "v2",
        false,
        chunkSize,
        maxFileSize,
        DEFAULT_REQUEST_TIMEOUT,
        DEFAULT_UPLOAD_TIMEOUT,
        pollTimeout,
        pollInterval,
        DEFAULT_MAX_ATTEMPTS,
        true,
        "SELF_ONLY",
        false,
        false,
        false,
        1000,
        "");
  }

  public static TikTokPublisherProperties defaults(String accessToken, String apiBaseUrl) {
    return new TikTokPublisherProperties(
        accessToken,
        apiBaseUrl,
        DEFAULT_CHUNK_SIZE,
        DEFAULT_MAX_FILE_SIZE,
        DEFAULT_POLL_TIMEOUT,
        DEFAULT_POLL_INTERVAL);
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

  private static Duration nonNegative(Duration value, Duration fallback) {
    return value == null || value.isNegative() ? fallback : value;
  }
}
