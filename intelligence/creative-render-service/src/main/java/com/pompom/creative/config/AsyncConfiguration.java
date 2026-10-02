package com.pompom.creative.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;

/** Async task execution configuration. Enables @Async annotation for background processing. */
@Configuration
@EnableAsync
public class AsyncConfiguration {
  // Configuration in application.yml
}
