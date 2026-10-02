package com.pompomhills.intelligence.performance;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pompom.discovery-score")
public record DiscoveryScoreProperties(
    double nonFollowerWeight, double usAudienceWeight, double usAudienceTargetPercentage) {}
