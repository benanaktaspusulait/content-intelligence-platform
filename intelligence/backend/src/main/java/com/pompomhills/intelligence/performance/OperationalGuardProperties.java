package com.pompomhills.intelligence.performance;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pompom.operational-guards")
public record OperationalGuardProperties(
    boolean enabled,
    int minimumMatureObservations,
    int maturityHours,
    double recommendationPercentageFloor,
    double completionRateFloor,
    double averageWatchSecondsFloor,
    String policyVersion) {}
