package com.pompom.creative.config;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

/** Reports configuration gaps that would make the production lifecycle unsafe to operate. */
@Component("creativeRenderReadiness")
public class ProductionReadinessHealthIndicator implements HealthIndicator {

  private final Environment environment;
  private final boolean openArtEnabled;
  private final boolean mockEnabled;
  private final String qaUrl;
  private final String intelligenceUrl;
  private final String observationToken;
  private final String reviewToken;

  public ProductionReadinessHealthIndicator(
      Environment environment,
      @Value("${pompom.openart.enabled:false}") boolean openArtEnabled,
      @Value("${pompom.openart.mock.enabled:true}") boolean mockEnabled,
      @Value("${pompom.qa.service.url:}") String qaUrl,
      @Value("${pompom.intelligence-base-url:}") String intelligenceUrl,
      @Value("${pompom.observation-bridge-token:}") String observationToken,
      @Value("${pompom.qa.review-token:}") String reviewToken) {
    this.environment = environment;
    this.openArtEnabled = openArtEnabled;
    this.mockEnabled = mockEnabled;
    this.qaUrl = qaUrl;
    this.intelligenceUrl = intelligenceUrl;
    this.observationToken = observationToken;
    this.reviewToken = reviewToken;
  }

  @Override
  public Health health() {
    if (!Arrays.asList(environment.getActiveProfiles()).contains("production")) {
      return Health.up().withDetail("profile", "non-production").build();
    }
    List<String> missing = new ArrayList<>();
    if (!openArtEnabled || mockEnabled) missing.add("real OpenArt provider");
    if (qaUrl.isBlank()) missing.add("QA service URL");
    if (intelligenceUrl.isBlank()) missing.add("intelligence backend URL");
    if (observationToken.isBlank()) missing.add("observation bridge token");
    if (reviewToken.isBlank()) missing.add("QA review token");
    if (!missing.isEmpty()) {
      return Health.down().withDetail("missing", missing).build();
    }
    return Health.up().withDetail("profile", "production").build();
  }
}
