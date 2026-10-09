package com.pompom.creative.publisher.internal;

import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import java.util.Map;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties(PublisherServiceProperties.class)
public class InternalPublisherConfiguration {
  @Bean
  InternalPublisherRegistry internalPublisherRegistry(
      RestClient.Builder builder, PublisherServiceProperties properties) {
    return new InternalPublisherRegistry(
        Map.of(
            PlatformType.FACEBOOK,
                new InternalPublisherClient(
                    builder,
                    "facebook_reels",
                    properties.metaBaseUrl(),
                    properties.metaInternalToken(),
                    properties.metaEnabled()),
            PlatformType.INSTAGRAM,
                new InternalPublisherClient(
                    builder,
                    "instagram_reels",
                    properties.metaBaseUrl(),
                    properties.metaInternalToken(),
                    properties.metaEnabled()),
            PlatformType.TIKTOK,
                new InternalPublisherClient(
                    builder,
                    "tiktok_video",
                    properties.tiktokBaseUrl(),
                    properties.tiktokInternalToken(),
                    properties.tiktokEnabled()),
            PlatformType.YOUTUBE,
                new InternalPublisherClient(
                    builder,
                    "youtube_shorts",
                    properties.youtubeBaseUrl(),
                    properties.youtubeInternalToken(),
                    properties.youtubeEnabled())));
  }
}
