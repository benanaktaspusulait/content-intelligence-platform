package com.pompom.tiktokpublisher.security;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class TikTokWriteCapabilityGuardTest {

  @Test
  void rejectsLivePublishAndReconcileWhenTargetAccountIsBlank() {
    TikTokWriteCapabilityGuard guard =
        new TikTokWriteCapabilityGuard(true, true, false, "internal", "access-token", " ");

    assertThatThrownBy(() -> guard.assertProviderConfigured("tiktok_video", "account-1", true))
        .isInstanceOf(TikTokWriteCapabilityGuard.ForbiddenException.class);
    assertThatThrownBy(() -> guard.assertProviderConfigured("tiktok_video", "account-1", false))
        .isInstanceOf(TikTokWriteCapabilityGuard.ForbiddenException.class);
  }

  @Test
  void rejectsAccountMismatchAndAcceptsOnlyConfiguredTarget() {
    TikTokWriteCapabilityGuard guard =
        new TikTokWriteCapabilityGuard(true, true, false, "internal", "access-token", "account-1");

    assertThatThrownBy(() -> guard.assertProviderConfigured("tiktok_video", "account-2", true))
        .isInstanceOf(TikTokWriteCapabilityGuard.ForbiddenException.class);
    assertThatCode(() -> guard.assertProviderConfigured("tiktok_video", "account-1", true))
        .doesNotThrowAnyException();
  }
}
