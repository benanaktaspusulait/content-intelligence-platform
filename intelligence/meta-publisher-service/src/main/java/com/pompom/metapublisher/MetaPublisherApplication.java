package com.pompom.metapublisher;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishersupport.PublisherRequestValidator;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@SpringBootApplication
@EnableConfigurationProperties(MetaPublisherProperties.class)
public class MetaPublisherApplication {

  @Bean
  ObjectMapper objectMapper() {
    return new ObjectMapper();
  }

  @Bean
  RestClient.Builder restClientBuilder(MetaPublisherProperties properties) {
    return RestClient.builder()
        .requestFactory(MetaClientSupport.deadlineRequestFactory(properties));
  }

  @Bean
  PublisherRequestValidator publisherRequestValidator() {
    return new PublisherRequestValidator();
  }

  public static void main(String[] args) {
    SpringApplication.run(MetaPublisherApplication.class, args);
  }
}
