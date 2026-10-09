package com.pompom.creative.publisher.internal;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pompom.publishers")
public record PublisherServiceProperties(
    String metaBaseUrl,
    String tiktokBaseUrl,
    String youtubeBaseUrl,
    String metaInternalToken,
    String tiktokInternalToken,
    String youtubeInternalToken,
    boolean metaEnabled,
    boolean tiktokEnabled,
    boolean youtubeEnabled) {}
