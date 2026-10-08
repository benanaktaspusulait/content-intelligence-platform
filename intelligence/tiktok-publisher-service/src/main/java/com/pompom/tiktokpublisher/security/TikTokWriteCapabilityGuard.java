package com.pompom.tiktokpublisher.security;

import com.pompom.tiktokpublisher.TikTokPublisherProperties;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/** Fail-closed internal boundary for TikTok provider writes and reads. */
@Component
public class TikTokWriteCapabilityGuard {

  public static final String INTERNAL_TOKEN_HEADER = "X-Internal-Publisher-Token";
  public static final String CALLER_ENABLED_HEADER = "X-TikTok-Publish-Enabled";
  public static final String CAPABILITY_HEADER = "X-Publisher-Capability";
  public static final String CAPABILITY = "tiktok_video";

  private final boolean writeEnabled;
  private final boolean publishEnabled;
  private final boolean dryRun;
  private final String internalToken;
  private final String accessToken;
  private final String configuredPlatformAccountId;

  @Autowired
  public TikTokWriteCapabilityGuard(TikTokPublisherProperties properties) {
    this(
        properties.writeEnabled(),
        properties.publishEnabled(),
        properties.dryRun(),
        properties.internalToken(),
        properties.accessToken(),
        properties.platformAccountId());
  }

  public TikTokWriteCapabilityGuard(boolean enabled, String internalToken) {
    this(enabled, enabled, false, internalToken, "configured-for-test", "");
  }

  public TikTokWriteCapabilityGuard(
      boolean writeEnabled,
      boolean publishEnabled,
      boolean dryRun,
      String internalToken,
      String accessToken,
      String platformAccountId) {
    this.writeEnabled = writeEnabled;
    this.publishEnabled = publishEnabled;
    this.dryRun = dryRun;
    this.internalToken = valueOrEmpty(internalToken);
    this.accessToken = valueOrEmpty(accessToken);
    this.configuredPlatformAccountId = valueOrEmpty(platformAccountId);
  }

  public void assertInternalCaller(String presentedToken) {
    if (internalToken.isBlank()
        || presentedToken == null
        || !MessageDigest.isEqual(
            internalToken.getBytes(StandardCharsets.UTF_8),
            presentedToken.getBytes(StandardCharsets.UTF_8))) {
      throw new UnauthorizedException();
    }
  }

  public void assertPublishAllowed(
      String presentedToken, String callerEnabled, String capability, String platformAccountId) {
    assertInternalCaller(presentedToken);
    if (!"true".equalsIgnoreCase(callerEnabled)) {
      throw new ForbiddenException();
    }
    assertProviderConfigured(capability, platformAccountId, true);
  }

  public void assertProviderConfigured(
      String capability, String platformAccountId, boolean requireWriteFlags) {
    String normalizedCapability = normalizeCapability(capability);
    if (!CAPABILITY.equals(normalizedCapability)) {
      throw new UnsupportedCapabilityException();
    }
    if (requireWriteFlags && (!writeEnabled || !publishEnabled || dryRun)) {
      throw new ForbiddenException();
    }
    if (accessToken.isBlank()) {
      throw new ForbiddenException();
    }
    if (!configuredPlatformAccountId.isBlank()
        && !configuredPlatformAccountId.equals(platformAccountId)) {
      throw new ForbiddenException();
    }
  }

  public String normalizeCapability(String capability) {
    String normalized = capability == null ? "" : capability.trim().toLowerCase(Locale.ROOT);
    if (!CAPABILITY.equals(normalized)) {
      throw new UnsupportedCapabilityException();
    }
    return normalized;
  }

  private static String valueOrEmpty(String value) {
    return value == null ? "" : value;
  }

  public static class UnauthorizedException extends RuntimeException {
    public UnauthorizedException() {
      super("internal publisher authentication failed");
    }
  }

  public static class ForbiddenException extends RuntimeException {
    public ForbiddenException() {
      super("TikTok publishing is disabled or not configured");
    }
  }

  public static class UnsupportedCapabilityException extends RuntimeException {
    public UnsupportedCapabilityException() {
      super("unsupported publisher capability");
    }
  }
}
