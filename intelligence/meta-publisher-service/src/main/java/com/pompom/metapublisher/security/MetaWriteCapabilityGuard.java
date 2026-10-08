package com.pompom.metapublisher.security;

import com.pompom.metapublisher.MetaPublisherProperties;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class MetaWriteCapabilityGuard {

  public static final String INTERNAL_TOKEN_HEADER = "X-Internal-Publisher-Token";
  public static final String CALLER_ENABLED_HEADER = "X-Meta-Publish-Enabled";
  public static final String CAPABILITY_HEADER = "X-Publisher-Capability";

  private final boolean writeEnabled;
  private final boolean publishEnabled;
  private final String internalToken;
  private final String facebookPageId;
  private final String facebookPageAccessToken;
  private final String instagramAccountId;
  private final String instagramAccessToken;
  private final boolean requireProviderConfiguration;

  @Autowired
  public MetaWriteCapabilityGuard(MetaPublisherProperties properties) {
    this(
        properties.writeEnabled(),
        properties.publishEnabled(),
        properties.internalToken(),
        properties.facebookPageId(),
        properties.facebookPageAccessToken(),
        properties.instagramAccountId(),
        properties.instagramAccessToken(),
        true);
  }

  public MetaWriteCapabilityGuard(boolean enabled, String internalToken) {
    this(enabled, enabled, internalToken, "", "", "", "", false);
  }

  private MetaWriteCapabilityGuard(
      boolean writeEnabled,
      boolean publishEnabled,
      String internalToken,
      String facebookPageId,
      String facebookPageAccessToken,
      String instagramAccountId,
      String instagramAccessToken,
      boolean requireProviderConfiguration) {
    this.writeEnabled = writeEnabled;
    this.publishEnabled = publishEnabled;
    this.internalToken = valueOrEmpty(internalToken);
    this.facebookPageId = valueOrEmpty(facebookPageId);
    this.facebookPageAccessToken = valueOrEmpty(facebookPageAccessToken);
    this.instagramAccountId = valueOrEmpty(instagramAccountId);
    this.instagramAccessToken = valueOrEmpty(instagramAccessToken);
    this.requireProviderConfiguration = requireProviderConfiguration;
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

  public void assertPublishAllowed(String presentedToken, String callerEnabled, String capability) {
    assertPublishAllowed(presentedToken, callerEnabled, capability, null);
  }

  public void assertPublishAllowed(
      String presentedToken, String callerEnabled, String capability, String platformAccountId) {
    assertInternalCaller(presentedToken);
    if (!"true".equalsIgnoreCase(callerEnabled)) {
      throw new ForbiddenException();
    }
    assertProviderConfigured(capability, platformAccountId, true);
  }

  /**
   * Checks the service-owned provider configuration before a provider operation is claimed.
   * Reconciliation calls this with {@code requireWriteFlags=false} because provider reads are not
   * provider writes.
   */
  public void assertProviderConfigured(
      String capability, String platformAccountId, boolean requireWriteFlags) {
    if (requireWriteFlags && (!writeEnabled || !publishEnabled)) {
      throw new ForbiddenException();
    }
    String normalizedCapability = normalizeCapability(capability);
    if (!requireProviderConfiguration) {
      return;
    }
    if ("facebook_reels".equals(normalizedCapability)
        && (!matchesConfiguredTarget(platformAccountId, facebookPageId)
            || facebookPageAccessToken.isBlank())) {
      throw new ForbiddenException();
    }
    if ("instagram_reels".equals(normalizedCapability)
        && (!matchesConfiguredTarget(platformAccountId, instagramAccountId)
            || instagramAccessToken.isBlank())) {
      throw new ForbiddenException();
    }
  }

  public String normalizeCapability(String capability) {
    String normalized = capability == null ? "" : capability.trim().toLowerCase(Locale.ROOT);
    if (!"facebook_reels".equals(normalized) && !"instagram_reels".equals(normalized)) {
      throw new UnsupportedCapabilityException();
    }
    return normalized;
  }

  private boolean matchesConfiguredTarget(String requested, String configured) {
    return requested != null && !requested.isBlank() && requested.equals(configured);
  }

  private String valueOrEmpty(String value) {
    return value == null ? "" : value;
  }

  public static class UnauthorizedException extends RuntimeException {
    public UnauthorizedException() {
      super("internal publisher authentication failed");
    }
  }

  public static class ForbiddenException extends RuntimeException {
    public ForbiddenException() {
      super("Meta publishing is disabled");
    }
  }

  public static class UnsupportedCapabilityException extends RuntimeException {
    public UnsupportedCapabilityException() {
      super("unsupported publisher capability");
    }
  }
}
