package com.pompom.creative.config;

import com.pompom.creative.openart.CliMockOpenArtAdapter;
import com.pompom.creative.openart.CliRealOpenArtAdapter;
import com.pompom.creative.openart.OpenArtAdapter;
import java.nio.file.Path;
import java.nio.file.Paths;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.env.Environment;

/**
 * Configuration for OpenArt adapter selection.
 *
 * <p>Provides either real or mock adapter based on configuration.
 */
@Configuration
@Slf4j
public class OpenArtConfiguration {

  @Value("${pompom.openart.enabled:false}")
  private boolean openartEnabled;

  @Value("${pompom.openart.mock.enabled:true}")
  private boolean mockEnabled;

  @Value("${pompom.data.root:../data}")
  private String dataRoot;

  private final Environment environment;

  public OpenArtConfiguration(Environment environment) {
    this.environment = environment;
  }

  /** Primary OpenArt adapter bean. Uses real adapter if enabled, otherwise falls back to mock. */
  @Bean
  @Primary
  public OpenArtAdapter openArtAdapter(CliRealOpenArtAdapter realAdapter) {
    boolean production = java.util.Arrays.asList(environment.getActiveProfiles()).contains("production");
    if (production && (!openartEnabled || mockEnabled)) {
      throw new IllegalStateException(
          "Production requires the real OpenArt provider and forbids the mock provider");
    }
    if (openartEnabled) {
      if (production && !realAdapter.isAvailable()) {
        throw new IllegalStateException("OpenArt runtime is unavailable in production");
      }
      log.info("Using REAL OpenArt adapter (CLI-based)");
      return realAdapter;
    } else if (mockEnabled) {
      log.info("Using MOCK OpenArt adapter (testing/development)");
      Path workDir = Paths.get(dataRoot, "openart-mock");
      return new CliMockOpenArtAdapter(workDir);
    } else {
      throw new IllegalStateException(
          "No OpenArt adapter configured. Set either "
              + "pompom.openart.enabled=true (real) or "
              + "pompom.openart.mock.enabled=true (mock)");
    }
  }
}
