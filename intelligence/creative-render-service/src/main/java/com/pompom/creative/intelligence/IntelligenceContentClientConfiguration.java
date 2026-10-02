package com.pompom.creative.intelligence;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Wires the {@link RestClient} used to reach the intelligence bounded context.
 *
 * <p>The factory is given bounded connect/read timeouts so a slow or hung intelligence service
 * cannot block a render worker thread (and the DB connection it may hold) indefinitely. A read
 * timeout surfaces as a {@link java.net.SocketTimeoutException}, which {@link
 * HttpIntelligenceContentClient} maps to {@link IntelligenceContentTimeoutException}.
 */
@Configuration
public class IntelligenceContentClientConfiguration {

  @Bean("intelligenceRestClient")
  RestClient intelligenceRestClient(
      RestClient.Builder builder,
      @Value("${pompom.intelligence-base-url}") String intelligenceBaseUrl,
      @Value("${pompom.intelligence-client.connect-timeout:2s}") Duration connectTimeout,
      @Value("${pompom.intelligence-client.read-timeout:5s}") Duration readTimeout) {
    SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
    requestFactory.setConnectTimeout((int) connectTimeout.toMillis());
    requestFactory.setReadTimeout((int) readTimeout.toMillis());
    return builder.baseUrl(intelligenceBaseUrl).requestFactory(requestFactory).build();
  }
}
