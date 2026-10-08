package com.pompom.youtubepublisher.security;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class YouTubeWriteCapabilityGuardTest {

  @Test
  void rejectsWritesWhenServiceIsDisabledOrAccountDoesNotMatch() {
    YouTubeWriteCapabilityGuard disabled =
        new YouTubeWriteCapabilityGuard(false, true, false, "internal", true, "account-1");
    YouTubeWriteCapabilityGuard configured =
        new YouTubeWriteCapabilityGuard(true, true, false, "internal", true, "account-1");

    assertThatThrownBy(() -> disabled.assertProviderConfigured("youtube_shorts", "account-1", true))
        .isInstanceOf(YouTubeWriteCapabilityGuard.ForbiddenException.class);
    assertThatThrownBy(
            () -> configured.assertProviderConfigured("youtube_shorts", "account-2", true))
        .isInstanceOf(YouTubeWriteCapabilityGuard.ForbiddenException.class);
    assertThatCode(() -> configured.assertProviderConfigured("youtube_shorts", "account-1", false))
        .doesNotThrowAnyException();
  }

  @Test
  void comparesInternalTokenAndRejectsOtherCapabilities() {
    YouTubeWriteCapabilityGuard guard =
        new YouTubeWriteCapabilityGuard(true, true, false, "internal", true, "account-1");

    assertThatCode(() -> guard.assertInternalCaller("internal")).doesNotThrowAnyException();
    assertThatThrownBy(() -> guard.assertInternalCaller("wrong"))
        .isInstanceOf(YouTubeWriteCapabilityGuard.UnauthorizedException.class);
    assertThatThrownBy(() -> guard.normalizeCapability("tiktok_video"))
        .isInstanceOf(YouTubeWriteCapabilityGuard.UnsupportedCapabilityException.class);
  }
}
