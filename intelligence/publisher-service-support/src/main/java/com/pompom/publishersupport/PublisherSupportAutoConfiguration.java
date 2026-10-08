package com.pompom.publishersupport;

import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.flyway.autoconfigure.FlywayAutoConfiguration;
import org.springframework.boot.flyway.autoconfigure.FlywayMigrationInitializer;
import org.springframework.boot.persistence.autoconfigure.EntityScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.DependsOn;
import org.springframework.context.annotation.Import;

/**
 * Auto-registers support persistence and its isolated migration history for publisher consumers.
 */
@AutoConfiguration(after = FlywayAutoConfiguration.class)
@EntityScan(basePackageClasses = ProviderOperationRecord.class)
@Import(ProviderOperationRepository.class)
public class PublisherSupportAutoConfiguration {

  @Bean(name = "publisherSupportFlyway")
  @ConditionalOnBean(DataSource.class)
  @ConditionalOnProperty(
      prefix = "publisher.support.flyway",
      name = "enabled",
      havingValue = "true",
      matchIfMissing = true)
  @ConditionalOnMissingBean(name = "publisherSupportFlyway")
  Flyway publisherSupportFlyway(DataSource dataSource) {
    return Flyway.configure()
        .dataSource(dataSource)
        .locations(PublisherSupportFlywayConfiguration.MIGRATION_LOCATION)
        .schemas(PublisherSupportFlywayConfiguration.SCHEMA)
        .defaultSchema(PublisherSupportFlywayConfiguration.SCHEMA)
        .table(PublisherSupportFlywayConfiguration.HISTORY_TABLE)
        .createSchemas(true)
        .load();
  }

  @Bean(name = "publisherSupportFlywayInitializer")
  @DependsOn("flywayInitializer")
  @ConditionalOnBean(name = {"publisherSupportFlyway", "flywayInitializer"})
  FlywayMigrationInitializer publisherSupportFlywayInitializerAfterConsumerFlyway(
      @Qualifier("publisherSupportFlyway") Flyway publisherSupportFlyway) {
    return new FlywayMigrationInitializer(publisherSupportFlyway);
  }

  @Bean(name = "publisherSupportFlywayInitializer")
  @ConditionalOnBean(name = "publisherSupportFlyway")
  @ConditionalOnMissingBean(name = "flywayInitializer")
  FlywayMigrationInitializer publisherSupportFlywayInitializerWithoutConsumerFlyway(
      @Qualifier("publisherSupportFlyway") Flyway publisherSupportFlyway) {
    return new FlywayMigrationInitializer(publisherSupportFlyway);
  }
}
