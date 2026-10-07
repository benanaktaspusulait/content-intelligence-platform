package com.pompom.creative.oauth;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Separate fail-closed guard for Meta public comment replies. */
@Component
public class MetaCommentReplyGuard {

  private final boolean enabled;

  @Autowired
  public MetaCommentReplyGuard(
      @Value("${pompom.meta.comment-reply-enabled:false}") String enabled) {
    this(Boolean.parseBoolean(enabled));
  }

  public MetaCommentReplyGuard(boolean enabled) {
    this.enabled = enabled;
  }

  public boolean isEnabled() {
    return enabled;
  }

  public void assertAllowed(PlatformType platform) {
    if ((platform == PlatformType.FACEBOOK || platform == PlatformType.INSTAGRAM) && !enabled) {
      throw new MetaCommentReplyDisabledException();
    }
  }
}
