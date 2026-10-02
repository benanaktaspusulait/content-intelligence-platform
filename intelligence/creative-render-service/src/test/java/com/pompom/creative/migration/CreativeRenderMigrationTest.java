package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Verifies that a clean run of the render service migrations builds the complete render-owned
 * schema inside {@code creative_render}, with its own independent Flyway history.
 */
@Testcontainers(disabledWithoutDocker = true)
class CreativeRenderMigrationTest {

  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  @BeforeAll
  static void runMigrations() {
    RenderMigrationSupport.migrate(DB);
  }

  @Test
  void createsAllRenderOwnedTablesUnderCreativeRenderSchema() {
    Set<String> tables = RenderMigrationSupport.tableNames(DB, "creative_render");

    assertThat(tables)
        .as("core render tables")
        .contains("render_jobs", "render_assets", "render_qa_results", "openart_credit_log");

    assertThat(tables).as("legacy copy audit table").contains("legacy_copy_audit");

    assertThat(tables)
        .as("publication tables")
        .contains(
            "publication_jobs",
            "platform_credentials",
            "scheduled_publications",
            "publication_analytics",
            "webhook_events");

    assertThat(tables).as("metrics tables").contains("video_metrics", "metrics_collection_jobs");

    assertThat(tables)
        .as("analytics / support tables")
        .contains(
            "performance_classifications",
            "trajectory_analyses",
            "correlation_analyses",
            "rule_candidates",
            "winner_entries",
            "notifications",
            "performance_predictions",
            "ab_tests",
            "follower_metrics",
            "reach_further_events");
  }

  @Test
  void keepsIndependentFlywayHistoryInCreativeRenderSchema() {
    assertThat(RenderMigrationSupport.tableNames(DB, "creative_render"))
        .as("render service owns its own Flyway history")
        .contains("flyway_schema_history");

    assertThat(RenderMigrationSupport.tableNames(DB, "public"))
        .as("render migrations must not create a Flyway history in the backend-owned public schema")
        .doesNotContain("flyway_schema_history");
  }
}
