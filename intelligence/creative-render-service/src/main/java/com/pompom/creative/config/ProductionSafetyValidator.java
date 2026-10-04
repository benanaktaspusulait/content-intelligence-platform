package com.pompom.creative.config;

import jakarta.annotation.PostConstruct;
import java.util.Arrays;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

/** Fails startup when production security can silently degrade into an unsafe mode. */
@Component
public class ProductionSafetyValidator {
  private final Environment environment;
  private final String encryptionKey;
  private final String facebookWebhookSecret;
  private final String instagramWebhookSecret;
  private final String tiktokWebhookSecret;
  private final String youtubeWebhookSecret;

  public ProductionSafetyValidator(
      Environment environment,
      @Value("${pompom.security.encryption.key:}") String encryptionKey,
      @Value("${pompom.webhooks.facebook.secret:}") String facebookWebhookSecret,
      @Value("${pompom.webhooks.instagram.secret:}") String instagramWebhookSecret,
      @Value("${pompom.webhooks.tiktok.secret:}") String tiktokWebhookSecret,
      @Value("${pompom.webhooks.youtube.secret:}") String youtubeWebhookSecret) {
    this.environment = environment;
    this.encryptionKey = encryptionKey;
    this.facebookWebhookSecret = facebookWebhookSecret;
    this.instagramWebhookSecret = instagramWebhookSecret;
    this.tiktokWebhookSecret = tiktokWebhookSecret;
    this.youtubeWebhookSecret = youtubeWebhookSecret;
  }

  @PostConstruct
  void validate() {
    if (!Arrays.asList(environment.getActiveProfiles()).contains("production")) {
      return;
    }
    require("POMPOM encryption key", encryptionKey);
    require("Facebook webhook secret", facebookWebhookSecret);
    require("Instagram webhook secret", instagramWebhookSecret);
    require("TikTok webhook secret", tiktokWebhookSecret);
    require("YouTube webhook secret", youtubeWebhookSecret);
  }

  private void require(String name, String value) {
    if (value == null || value.isBlank()) {
      throw new IllegalStateException(name + " is required in production");
    }
  }
}
