package com.pompom.creative.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

/** Scheduling configuration. Enables @Scheduled annotation for cron jobs. */
@Configuration
@EnableScheduling
public class SchedulingConfiguration {
  // Configuration enabled
}
