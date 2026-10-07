package com.pompomhills.intelligence.meta;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties(prefix = "pompom.meta")
public record MetaReadProperties(
    @DefaultValue("false") boolean enabled,
    @DefaultValue("v26.0") String apiVersion,
    @DefaultValue("") String pageId,
    @DefaultValue("") String instagramAccountId,
    @DefaultValue("") String accessToken,
    @DefaultValue("") String userAccessToken,
    @DefaultValue("5s") Duration connectTimeout,
    @DefaultValue("15s") Duration readTimeout,
    @DefaultValue("false") boolean publishEnabled,
    @DefaultValue("false") boolean commentReplyEnabled,
    @DefaultValue("default") String connectionOwnerKey,
    @DefaultValue("false") boolean diagnosticOverridesEnabled) {

  @ConstructorBinding
  public MetaReadProperties {
    apiVersion = normalizeApiVersion(apiVersion);
    pageId = normalizeText(pageId);
    instagramAccountId = normalizeText(instagramAccountId);
    accessToken = normalizeText(accessToken);
    userAccessToken = normalizeText(userAccessToken);
    connectTimeout = normalizeDuration(connectTimeout, Duration.ofSeconds(5));
    readTimeout = normalizeDuration(readTimeout, Duration.ofSeconds(15));
    connectionOwnerKey = normalizeOwnerKey(connectionOwnerKey);
  }

  /** Compatibility constructor for existing lifecycle tests and legacy bootstrap callers. */
  public MetaReadProperties(
      boolean enabled,
      String apiVersion,
      String pageId,
      String instagramAccountId,
      String accessToken,
      String userAccessToken,
      Duration connectTimeout,
      Duration readTimeout,
      boolean publishEnabled,
      boolean commentReplyEnabled,
      String connectionOwnerKey) {
    this(
        enabled,
        apiVersion,
        pageId,
        instagramAccountId,
        accessToken,
        userAccessToken,
        connectTimeout,
        readTimeout,
        publishEnabled,
        commentReplyEnabled,
        connectionOwnerKey,
        true);
  }

  /** Compatibility constructor for existing read-only unit tests and callers. */
  public MetaReadProperties(
      boolean enabled,
      String apiVersion,
      String pageId,
      String instagramAccountId,
      String accessToken,
      String userAccessToken,
      Duration connectTimeout,
      Duration readTimeout) {
    this(
        enabled,
        apiVersion,
        pageId,
        instagramAccountId,
        accessToken,
        userAccessToken,
        connectTimeout,
        readTimeout,
        false,
        false,
        "default",
        true);
  }

  /** Static credentials are retained only as an explicit bootstrap fallback. */
  public boolean isConfigured() {
    return isTargetConfigured() && !accessToken.isBlank();
  }

  public boolean isTargetConfigured() {
    return enabled
        && diagnosticOverridesEnabled
        && !pageId.isBlank()
        && !instagramAccountId.isBlank();
  }

  @Override
  public String toString() {
    return "MetaReadProperties[enabled="
        + enabled
        + ", apiVersion="
        + apiVersion
        + ", pageId="
        + pageId
        + ", instagramAccountId="
        + instagramAccountId
        + ", publishEnabled="
        + publishEnabled
        + ", commentReplyEnabled="
        + commentReplyEnabled
        + ", connectionOwnerKey="
        + connectionOwnerKey
        + ", connectTimeout="
        + connectTimeout
        + ", readTimeout="
        + readTimeout
        + "]";
  }

  private static String normalizeApiVersion(String value) {
    String normalized = normalizeText(value);
    if (normalized.isBlank()) {
      return "v26.0";
    }
    return normalized.startsWith("/") ? normalized.substring(1) : normalized;
  }

  private static String normalizeText(String value) {
    return value == null ? "" : value.trim();
  }

  private static String normalizeOwnerKey(String value) {
    String normalized = normalizeText(value);
    return normalized.isBlank() ? "default" : normalized;
  }

  private static Duration normalizeDuration(Duration value, Duration fallback) {
    return value == null || value.isNegative() || value.isZero() ? fallback : value;
  }
}
