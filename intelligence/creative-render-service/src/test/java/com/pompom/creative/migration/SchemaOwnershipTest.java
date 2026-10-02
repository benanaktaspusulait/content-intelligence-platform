package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Guards the physical schema boundary: the render service may own foreign keys only between its own
 * tables. No foreign key declared in {@code creative_render} may reference a table in the
 * backend-owned {@code public} schema (or any other schema).
 */
@Testcontainers(disabledWithoutDocker = true)
class SchemaOwnershipTest {

  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  @BeforeAll
  static void runMigrations() {
    RenderMigrationSupport.migrate(DB);
  }

  @Test
  void noForeignKeyFromCreativeRenderReferencesAnotherSchema() {
    List<String> crossSchemaForeignKeys =
        RenderMigrationSupport.crossSchemaForeignKeys(DB, "creative_render");

    assertThat(crossSchemaForeignKeys)
        .as("creative_render must not depend on public via foreign keys")
        .isEmpty();
  }
}
