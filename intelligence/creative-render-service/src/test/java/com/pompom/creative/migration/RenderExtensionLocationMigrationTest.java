package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/** Backend-first installation already places pgcrypto in public; render must not move it. */
@Testcontainers(disabledWithoutDocker = true)
class RenderExtensionLocationMigrationTest {
  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  @Test
  void migratesWithPublicCryptoAndPreservesExtensionOwnership() throws Exception {
    try (var connection = RenderMigrationSupport.connect(DB);
        var statement = connection.createStatement()) {
      statement.execute("CREATE EXTENSION pgcrypto WITH SCHEMA public");
    }
    RenderMigrationSupport.migrate(DB);
    try (var connection = RenderMigrationSupport.connect(DB);
        var statement = connection.createStatement()) {
      try (var row = statement.executeQuery(
          "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='pgcrypto'")) {
        assertThat(row.next()).isTrue();
        assertThat(row.getString(1)).isEqualTo("public");
      }
      try (var row = statement.executeQuery("SELECT count(*) FROM creative_render.flyway_schema_history WHERE success")) {
        assertThat(row.next()).isTrue();
        assertThat(row.getInt(1)).isGreaterThanOrEqualTo(8);
      }
    }
  }
}
