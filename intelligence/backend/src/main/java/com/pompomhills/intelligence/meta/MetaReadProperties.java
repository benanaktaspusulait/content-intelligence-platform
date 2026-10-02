package com.pompomhills.intelligence.meta;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
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
    @DefaultValue("15s") Duration readTimeout) {

  public MetaReadProperties {
    apiVersion = normalizeApiVersion(apiVersion);
    pageId = normalizeText(pageId);
    instagramAccountId = normalizeText(instagramAccountId);
    accessToken = normalizeText(accessToken);
    userAccessToken = normalizeText(userAccessToken);
    connectTimeout = normalizeDuration(connectTimeout, Duration.ofSeconds(5));
    readTimeout = normalizeDuration(readTimeout, Duration.ofSeconds(15));
  }

  public boolean isConfigured() {
    return enabled && !pageId.isBlank() && !instagramAccountId.isBlank() && !accessToken.isBlank();
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

  private static Duration normalizeDuration(Duration value, Duration fallback) {
    return value == null || value.isNegative() || value.isZero() ? fallback : value;
  }
}
