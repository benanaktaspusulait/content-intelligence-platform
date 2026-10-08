package com.pompom.youtubepublisher.security;

import com.pompom.youtubepublisher.YouTubePublisherProperties;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/** Fail-closed internal boundary for YouTube writes and reconciliation reads. */
@Component
public class YouTubeWriteCapabilityGuard {

  public static final String INTERNAL_TOKEN_HEADER = "X-Internal-Publisher-Token";
  public static final String CALLER_ENABLED_HEADER = "X-YouTube-Publish-Enabled";
  public static final String CAPABILITY_HEADER = "X-Publisher-Capability";
  public static final String CAPABILITY = "youtube_shorts";

  private final boolean writeEnabled;
  private final boolean publishEnabled;
  private final boolean dryRun;
  private final String internalToken;
  private final boolean credentialConfigured;
  private final String configuredPlatformAccountId;

  @Autowired
  public YouTubeWriteCapabilityGuard(YouTubePublisherProperties properties) {
    this(
        properties.writeEnabled(),
        properties.publishEnabled(),
        properties.dryRun(),
        properties.internalToken(),
        properties.hasCredentialConfiguration(),
        properties.platformAccountId());
  }

  public YouTubeWriteCapabilityGuard(boolean enabled, String internalToken) {
    this(enabled, enabled, false, internalToken, true, "");
  }

  public YouTubeWriteCapabilityGuard(
      boolean writeEnabled,
      boolean publishEnabled,
      boolean dryRun,
      String internalToken,
      boolean credentialConfigured,
      String platformAccountId) {
    this.writeEnabled = writeEnabled;
    this.publishEnabled = publishEnabled;
    this.dryRun = dryRun;
    this.internalToken = valueOrEmpty(internalToken);
    this.credentialConfigured = credentialConfigured;
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
    if (!credentialConfigured
        || configuredPlatformAccountId.isBlank()
        || platformAccountId == null
        || !configuredPlatformAccountId.equals(platformAccountId)) {
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
      super("YouTube publishing is disabled or not configured");
    }
  }

  public static class UnsupportedCapabilityException extends RuntimeException {
    public UnsupportedCapabilityException() {
      super("unsupported publisher capability");
    }
  }
}
