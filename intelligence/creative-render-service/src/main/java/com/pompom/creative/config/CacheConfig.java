package com.pompom.creative.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Configuration;

/** Cache configuration for performance optimization. */
@Configuration
@EnableCaching
public class CacheConfig {
  // Spring Boot auto-configures simple cache
  // For production, use Redis with @Cacheable annotations
}
