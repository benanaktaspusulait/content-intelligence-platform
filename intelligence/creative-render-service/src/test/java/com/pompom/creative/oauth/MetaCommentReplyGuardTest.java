package com.pompom.creative.oauth;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class MetaCommentReplyGuardTest {

  @Test
  void blocksFacebookAndInstagramCommentRepliesByDefault() {
    MetaCommentReplyGuard guard = new MetaCommentReplyGuard(false);

    assertThatThrownBy(() -> guard.assertAllowed(PlatformType.FACEBOOK))
        .isInstanceOf(MetaCommentReplyDisabledException.class);
    assertThatThrownBy(() -> guard.assertAllowed(PlatformType.INSTAGRAM))
        .isInstanceOf(MetaCommentReplyDisabledException.class);
  }

  @Test
  void nonMetaPlatformsAreNotAffected() {
    MetaCommentReplyGuard guard = new MetaCommentReplyGuard(false);

    assertThatCode(() -> guard.assertAllowed(PlatformType.TIKTOK)).doesNotThrowAnyException();
    assertThatCode(() -> guard.assertAllowed(PlatformType.YOUTUBE)).doesNotThrowAnyException();
  }
}
