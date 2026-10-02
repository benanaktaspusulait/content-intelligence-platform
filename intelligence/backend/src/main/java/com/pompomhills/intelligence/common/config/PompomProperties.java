package com.pompomhills.intelligence.common.config;

import java.nio.file.Path;
import java.util.Set;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pompom")
public record PompomProperties(
    Path dataRoot,
    String mlBaseUrl,
    Set<String> allowedVideoExtensions,
    int reachFurtherEarlyHours,
    int reachFurtherMidHours) {}
