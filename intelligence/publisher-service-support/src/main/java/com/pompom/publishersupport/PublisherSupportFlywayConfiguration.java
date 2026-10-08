package com.pompom.publishersupport;

/** Explicit Flyway ownership contract for the shared publisher-support schema and history. */
public final class PublisherSupportFlywayConfiguration {

  public static final String MIGRATION_LOCATION = "classpath:db/publisher-support-migration";
  public static final String SCHEMA = "publisher_support";
  public static final String HISTORY_TABLE = "publisher_support_schema_history";

  private PublisherSupportFlywayConfiguration() {}
}
