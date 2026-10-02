package com.pompomhills.intelligence;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.web.client.RestClient;

@EnableJpaAuditing
@EnableScheduling
@SpringBootApplication
public class PompomCreativeIntelligenceApplication {
  public static void main(String[] args) {
    SpringApplication.run(PompomCreativeIntelligenceApplication.class, args);
  }

  @Bean
  public RestClient.Builder restClientBuilder() {
    return RestClient.builder();
  }

  @Bean
  public ObjectMapper objectMapper() {
    return new ObjectMapper();
  }
}
