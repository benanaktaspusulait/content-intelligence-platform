package com.pompom.creative;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.worker.RenderWorkerProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.web.client.RestClient;

@EnableJpaAuditing
@EnableScheduling
@EnableConfigurationProperties(RenderWorkerProperties.class)
@SpringBootApplication
public class CreativeRenderServiceApplication {

  public static void main(String[] args) {
    SpringApplication.run(CreativeRenderServiceApplication.class, args);
  }

  @Bean
  RestClient.Builder restClientBuilder() {
    return RestClient.builder();
  }

  @Bean
  ObjectMapper objectMapper() {
    return new ObjectMapper();
  }
}
