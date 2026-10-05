package com.pompomhills.intelligence.common.config;

import com.pompomhills.intelligence.performance.DiscoveryScoreProperties;
import com.pompomhills.intelligence.performance.OperationalGuardProperties;
import java.time.Clock;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
@EnableConfigurationProperties({
  PompomProperties.class, DiscoveryScoreProperties.class, OperationalGuardProperties.class
})
public class AppConfiguration {
  @Bean
  Clock clock() {
    return Clock.systemUTC();
  }

  @Bean
  RestClient mlRestClient(PompomProperties properties) {
    return RestClient.builder()
        .requestFactory(new SimpleClientHttpRequestFactory())
        .baseUrl(properties.mlBaseUrl())
        .build();
  }
}
