package com.pompom.creative.oauth;

/** Supported social media platforms for OAuth integration. */
public enum PlatformType {
  TIKTOK(
      "TikTok",
      "https://www.tiktok.com/v2/auth/authorize/",
      "https://open.tiktokapis.com/v2/oauth/token/"),
  YOUTUBE(
      "YouTube",
      "https://accounts.google.com/o/oauth2/v2/auth",
      "https://oauth2.googleapis.com/token"),
  FACEBOOK(
      "Facebook",
      "https://www.facebook.com/v26.0/dialog/oauth",
      "https://graph.facebook.com/v26.0/oauth/access_token"),
  INSTAGRAM(
      "Instagram",
      "https://api.instagram.com/oauth/authorize",
      "https://api.instagram.com/oauth/access_token");

  private final String displayName;
  private final String authorizationUrl;
  private final String tokenUrl;

  PlatformType(String displayName, String authorizationUrl, String tokenUrl) {
    this.displayName = displayName;
    this.authorizationUrl = authorizationUrl;
    this.tokenUrl = tokenUrl;
  }

  public String getDisplayName() {
    return displayName;
  }

  public String getAuthorizationUrl() {
    return authorizationUrl;
  }

  public String getTokenUrl() {
    return tokenUrl;
  }
}
