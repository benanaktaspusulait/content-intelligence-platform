package com.pompom.youtubepublisher;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.youtubepublisher.client.YouTubeDataClient;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@SpringBootApplication
@EnableConfigurationProperties(YouTubePublisherProperties.class)
public class YouTubePublisherApplication {

  @Bean
  ObjectMapper objectMapper() {
    return new ObjectMapper();
  }

  @Bean
  RestClient.Builder restClientBuilder(YouTubePublisherProperties properties) {
    return RestClient.builder()
        .requestFactory(YouTubeDataClient.deadlineRequestFactory(properties));
  }

  @Bean
  PublisherRequestValidator publisherRequestValidator() {
    return new PublisherRequestValidator();
  }

  public static void main(String[] args) {
    SpringApplication.run(YouTubePublisherApplication.class, args);
  }
}
