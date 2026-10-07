package com.pompom.creative.oauth;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class MetaPublicationGuardTest {

  @Test
  void blocksFacebookAndInstagramByDefault() {
    MetaPublicationGuard guard = new MetaPublicationGuard(false);

    assertThatThrownBy(() -> guard.assertAllowed(PlatformType.FACEBOOK))
        .isInstanceOf(MetaPublishingDisabledException.class);
    assertThatThrownBy(() -> guard.assertAllowed(PlatformType.INSTAGRAM))
        .isInstanceOf(MetaPublishingDisabledException.class);
  }

  @Test
  void leavesNonMetaPlatformsAvailableWhenMetaPublishingIsDisabled() {
    MetaPublicationGuard guard = new MetaPublicationGuard(false);

    assertThatCode(() -> guard.assertAllowed(PlatformType.TIKTOK)).doesNotThrowAnyException();
    assertThatCode(() -> guard.assertAllowed(PlatformType.YOUTUBE)).doesNotThrowAnyException();
  }
}
