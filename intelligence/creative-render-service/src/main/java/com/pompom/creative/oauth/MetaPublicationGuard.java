package com.pompom.creative.oauth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Server-side fail-closed guard for Meta write operations. */
@Component
public class MetaPublicationGuard {

  private final boolean enabled;

  public MetaPublicationGuard(@Value("${pompom.meta.publish-enabled:false}") String enabled) {
    this(Boolean.parseBoolean(enabled));
  }

  MetaPublicationGuard(boolean enabled) {
    this.enabled = enabled;
  }

  public boolean isEnabled() {
    return enabled;
  }

  public void assertAllowed(PlatformType platform) {
    if ((platform == PlatformType.FACEBOOK || platform == PlatformType.INSTAGRAM) && !enabled) {
      throw new MetaPublishingDisabledException();
    }
  }
}
