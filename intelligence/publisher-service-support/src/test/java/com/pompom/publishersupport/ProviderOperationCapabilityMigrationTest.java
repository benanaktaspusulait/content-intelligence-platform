package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.UUID;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

class ProviderOperationCapabilityMigrationTest {

  @Test
  void backfillsPopulatedV1RowsAndAllowsSameKeyInDifferentCapabilityScopes() {
    String url =
        "jdbc:h2:mem:provider_operation_capability_migration_"
            + UUID.randomUUID()
            + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1";
    DriverManagerDataSource dataSource = new DriverManagerDataSource(url, "sa", "");
    Flyway flywayV1 =
        Flyway.configure()
            .target("1")
            .dataSource(dataSource)
            .locations("classpath:db/publisher-support-migration")
            .schemas("publisher_support")
            .defaultSchema("publisher_support")
            .table("publisher_support_schema_history")
            .load();
    flywayV1.migrate();
    JdbcTemplate jdbc = new JdbcTemplate(dataSource);

    insertV1Row(jdbc, "facebook_reels:old-key");
    insertV1Row(jdbc, "instagram_reels:old-key");
    insertV1Row(jdbc, "legacy-key");
    assertThat(
            jdbc.queryForObject(
                "select count(*) from publisher_support.provider_operation_records", Integer.class))
        .isEqualTo(3);
    Flyway flyway =
        Flyway.configure()
            .dataSource(dataSource)
            .locations("classpath:db/publisher-support-migration")
            .schemas("publisher_support")
            .defaultSchema("publisher_support")
            .table("publisher_support_schema_history")
            .load();
    flyway.migrate();

    assertThat(capability(jdbc, "facebook_reels:old-key")).isEqualTo("facebook_reels");
    assertThat(capability(jdbc, "instagram_reels:old-key")).isEqualTo("instagram_reels");
    assertThat(capability(jdbc, "legacy-key")).isEqualTo("legacy");

    insertV2Row(jdbc, "facebook_reels:old-key", "instagram_reels");

    assertThat(
            jdbc.queryForObject(
                "select count(*) from publisher_support.provider_operation_records "
                    + "where command_idempotency_key = ?",
                Integer.class,
                "facebook_reels:old-key"))
        .isEqualTo(2);
  }

  private void insertV1Row(JdbcTemplate jdbc, String key) {
    jdbc.update(
        "insert into publisher_support.provider_operation_records "
            + "(id, publication_job_id, publication_attempt_id, command_idempotency_key, "
            + "command_fingerprint, started_at, reconciliation_required, created_at, updated_at, "
            + "entity_version) values (?, ?, ?, ?, ?, current_timestamp, false, current_timestamp, "
            + "current_timestamp, 0)",
        UUID.randomUUID(),
        UUID.randomUUID(),
        UUID.randomUUID(),
        key,
        "a".repeat(64));
  }

  private void insertV2Row(JdbcTemplate jdbc, String key, String capability) {
    jdbc.update(
        "insert into publisher_support.provider_operation_records "
            + "(id, publication_job_id, publication_attempt_id, command_idempotency_key, "
            + "publisher_capability, command_fingerprint, started_at, reconciliation_required, "
            + "created_at, updated_at, entity_version) values (?, ?, ?, ?, ?, ?, current_timestamp, "
            + "false, current_timestamp, current_timestamp, 0)",
        UUID.randomUUID(),
        UUID.randomUUID(),
        UUID.randomUUID(),
        key,
        capability,
        "b".repeat(64));
  }

  private String capability(JdbcTemplate jdbc, String key) {
    return jdbc.queryForObject(
        "select publisher_capability from publisher_support.provider_operation_records "
            + "where command_idempotency_key = ? order by id limit 1",
        String.class,
        key);
  }
}
