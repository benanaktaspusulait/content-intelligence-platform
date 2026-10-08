package com.pompom.metapublisher;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pompom.meta")
public record MetaPublisherProperties(
    boolean writeEnabled,
    boolean publishEnabled,
    String internalToken,
    String graphVersion,
    String graphBaseUrl,
    String ruploadBaseUrl,
    String facebookPageId,
    String facebookPageAccessToken,
    String instagramAccountId,
    String instagramAccessToken,
    Duration requestTimeout,
    Duration uploadTimeout,
    Duration pollTimeout,
    Duration pollInterval,
    int maxAttempts,
    boolean shareToFeed,
    String facebookReelTitle,
    String storageBackend,
    String storageDirectory,
    String storageBaseUrl,
    String storageUrlTemplate,
    boolean storageCleanup) {}
