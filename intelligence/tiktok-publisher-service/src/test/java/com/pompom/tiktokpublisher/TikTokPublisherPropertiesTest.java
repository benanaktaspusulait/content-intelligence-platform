package com.pompom.tiktokpublisher;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Duration;
import org.junit.jupiter.api.Test;

class TikTokPublisherPropertiesTest {

  @Test
  void usesThePythonProviderCeilingAsTheRuntimeDefaultAndClampsLargerValues() {
    TikTokPublisherProperties defaults =
        TikTokPublisherProperties.defaults("token", "https://open.tiktok.test");
    TikTokPublisherProperties configured =
        new TikTokPublisherProperties(
            true,
            true,
            "internal",
            "token",
            "https://open.tiktok.test",
            "v2",
            false,
            4,
            TikTokPublisherProperties.DEFAULT_MAX_FILE_SIZE + 1,
            Duration.ofSeconds(1),
            Duration.ofSeconds(1),
            Duration.ofSeconds(1),
            Duration.ZERO,
            1,
            true,
            "SELF_ONLY",
            false,
            false,
            false,
            1000,
            "account-1");

    assertThat(TikTokPublisherProperties.DEFAULT_MAX_FILE_SIZE)
        .isEqualTo(287L * 1024 * 1024);
    assertThat(defaults.maxFileSize()).isEqualTo(287L * 1024 * 1024);
    assertThat(configured.maxFileSize()).isEqualTo(287L * 1024 * 1024);
  }
}
