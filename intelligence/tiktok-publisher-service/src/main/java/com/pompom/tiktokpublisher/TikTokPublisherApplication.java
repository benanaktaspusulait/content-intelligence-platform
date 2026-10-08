package com.pompom.tiktokpublisher;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.tiktokpublisher.client.TikTokContentClient;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@SpringBootApplication
@EnableConfigurationProperties(TikTokPublisherProperties.class)
public class TikTokPublisherApplication {

  @Bean
  ObjectMapper objectMapper() {
    return new ObjectMapper();
  }

  @Bean
  RestClient.Builder restClientBuilder(TikTokPublisherProperties properties) {
    return RestClient.builder()
        .requestFactory(TikTokContentClient.deadlineRequestFactory(properties));
  }

  @Bean
  PublisherRequestValidator publisherRequestValidator() {
    return new PublisherRequestValidator();
  }

  public static void main(String[] args) {
    SpringApplication.run(TikTokPublisherApplication.class, args);
  }
}
