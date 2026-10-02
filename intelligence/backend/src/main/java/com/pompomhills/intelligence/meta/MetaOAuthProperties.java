package com.pompomhills.intelligence.meta;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * Configuration for the Meta OAuth authorization flow. The app secret is used only server-side for
 * the authorization-code/token exchange; it is never exposed to the browser, logs, or DTOs.
 */
@ConfigurationProperties(prefix = "pompom.meta.oauth")
public record MetaOAuthProperties(
    @DefaultValue("") String appId,
    @DefaultValue("") String appSecret,
    @DefaultValue("") String redirectUri) {

  public MetaOAuthProperties {
    appId = normalize(appId);
    appSecret = normalize(appSecret);
    redirectUri = normalize(redirectUri);
  }

  public boolean isConfigured() {
    return !appId.isBlank() && !appSecret.isBlank() && !redirectUri.isBlank();
  }

  @Override
  public String toString() {
    return "MetaOAuthProperties[appId=" + appId + ", redirectUri=" + redirectUri + "]";
  }

  private static String normalize(String value) {
    return value == null ? "" : value.trim();
  }
}
