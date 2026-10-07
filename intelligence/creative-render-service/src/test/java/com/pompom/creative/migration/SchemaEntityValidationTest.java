package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.sql.Connection;
import java.sql.Statement;
import java.util.List;
import org.hibernate.SessionFactory;
import org.hibernate.cfg.Configuration;
import org.hibernate.tool.schema.spi.SchemaManagementException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Boot-time entity/schema validation for the render service.
 *
 * <p>Production runs with {@code hibernate.ddl-auto=none}, so Hibernate never checks the mapped
 * entities against the physical {@code creative_render} schema at startup. This test closes that
 * gap: it migrates a disposable PostgreSQL container with the real Flyway migrations and then boots
 * Hibernate with {@code hibernate.hbm2ddl.auto=validate} over every render JPA entity (render
 * orchestration + publication/metrics/analytics/support). Validation fails the build if any entity
 * field maps to a column that the V1 migration does not create (or with an incompatible type), so a
 * future entity change that drifts from the schema is caught here instead of at runtime.
 *
 * <p>The Spring Boot naming strategies are applied explicitly so that entities relying on implicit
 * camelCase -&gt; snake_case naming (e.g. {@link com.pompom.creative.notification.Notification})
 * are validated exactly as they are mapped when the application boots.
 */
@Testcontainers(disabledWithoutDocker = true)
class SchemaEntityValidationTest {

  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  /**
   * Every {@code @Entity} managed by this module. Kept explicit (rather than classpath scanned) so
   * the test is an auditable manifest: a newly added entity that is not validated here will be
   * noticed in review.
   */
  private static final List<Class<?>> RENDER_ENTITIES =
      List.of(
          com.pompom.creative.domain.RenderJob.class,
          com.pompom.creative.domain.RenderAttempt.class,
          com.pompom.creative.domain.RenderAsset.class,
          com.pompom.creative.domain.MetaCommentThread.class,
          com.pompom.creative.domain.MetaComment.class,
          com.pompom.creative.domain.MetaCommentReply.class,
          com.pompom.creative.domain.MetaCommentDeliveryAttempt.class,
          com.pompom.creative.domain.RenderQaResult.class,
          com.pompom.creative.domain.OpenArtCreditLog.class,
          com.pompom.creative.openart.OpenArtReferenceAsset.class,
          com.pompom.creative.domain.PlatformCredential.class,
          com.pompom.creative.domain.PublicationJob.class,
          com.pompom.creative.domain.PublicationAnalytics.class,
          com.pompom.creative.domain.ScheduledPublication.class,
          com.pompom.creative.domain.WebhookEvent.class,
          com.pompom.creative.metrics.VideoMetrics.class,
          com.pompom.creative.metrics.MetricsCollectionJob.class,
          com.pompom.creative.performance.PerformanceClassification.class,
          com.pompom.creative.performance.FollowerMetrics.class,
          com.pompom.creative.performance.ReachFurtherEvent.class,
          com.pompom.creative.trajectory.TrajectoryAnalysis.class,
          com.pompom.creative.correlation.CorrelationAnalysis.class,
          com.pompom.creative.rulemining.RuleCandidate.class,
          com.pompom.creative.benchmark.WinnerEntry.class,
          com.pompom.creative.notification.Notification.class,
          com.pompom.creative.analytics.PerformancePrediction.class,
          com.pompom.creative.analytics.ABTest.class,
          com.pompom.creative.postrender.PostRenderEvaluation.class,
          com.pompom.creative.postrender.PostRenderRuleResultEntity.class,
          com.pompom.creative.postrender.PostRenderAssessmentEntity.class);

  @BeforeAll
  static void migrate() {
    RenderMigrationSupport.migrate(DB);
  }

  @Test
  void everyRenderEntityValidatesAgainstTheMigratedCreativeRenderSchema() {
    Configuration cfg = validatingConfiguration(RenderMigrationSupport.SCHEMA);
    RENDER_ENTITIES.forEach(cfg::addAnnotatedClass);

    // buildSessionFactory() runs Hibernate schema validation; a column/type mismatch throws.
    try (SessionFactory sf = cfg.buildSessionFactory()) {
      // Guard against vacuously validating nothing: all declared entities must be mapped.
      assertThat(sf.getMetamodel().getEntities()).hasSize(RENDER_ENTITIES.size());
    }
  }

  @Test
  void validationFailsWhenAnEntityFieldHasNoMatchingColumn() throws Exception {
    // Build an isolated schema whose render_jobs table deliberately omits the prompt_sha256 column
    // mapped by RenderJob#promptSha256. Validation must detect the missing column and abort.
    final String probeSchema = "entity_validation_probe";
    try (Connection c = RenderMigrationSupport.connect(DB);
        Statement st = c.createStatement()) {
      st.execute("DROP SCHEMA IF EXISTS " + probeSchema + " CASCADE");
      st.execute("CREATE SCHEMA " + probeSchema);
      st.execute(
          "CREATE TABLE "
              + probeSchema
              + ".render_jobs ("
              + " id UUID PRIMARY KEY,"
              + " content_id BIGINT NOT NULL,"
              + " prompt_version_id BIGINT NOT NULL,"
              + " content_title_snapshot VARCHAR(255) NOT NULL,"
              + " prompt_version_number_snapshot INT NOT NULL,"
              // prompt_sha256 intentionally omitted -- this is the drift we expect to be caught.
              + " prompt_text_snapshot TEXT NOT NULL,"
              + " validation_record_id BIGINT,"
              + " evidence_deterministic_ruleset_version TEXT,"
              + " evidence_semantic_provider TEXT,"
              + " evidence_semantic_model_version TEXT,"
              + " evidence_producibility_validator_version TEXT,"
              + " evidence_independent_revalidation_id UUID,"
              + " evidence_independently_revalidated_at TIMESTAMPTZ,"
              + " evidence_validated_at TIMESTAMPTZ,"
              + " idempotency_key TEXT,"
              + " request_fingerprint VARCHAR(64),"
              + " job_type VARCHAR(20) NOT NULL,"
              + " openart_job_id VARCHAR(100),"
              + " openart_model VARCHAR(50) NOT NULL,"
              + " openart_params JSONB,"
              + " status VARCHAR(30) NOT NULL,"
              + " attempt_number INT NOT NULL,"
              + " max_attempts INT NOT NULL,"
              + " credits_estimated NUMERIC(10,2),"
              + " credits_actual NUMERIC(10,2),"
              + " queued_at TIMESTAMPTZ NOT NULL,"
              + " started_at TIMESTAMPTZ,"
              + " completed_at TIMESTAMPTZ,"
              + " failed_at TIMESTAMPTZ,"
              + " error_code VARCHAR(50),"
              + " error_message TEXT,"
              + " created_at TIMESTAMPTZ NOT NULL,"
              + " updated_at TIMESTAMPTZ NOT NULL,"
              + " entity_version INT NOT NULL)");
    }

    Configuration cfg = validatingConfiguration(probeSchema);
    cfg.addAnnotatedClass(com.pompom.creative.domain.RenderJob.class);

    assertThatThrownBy(() -> cfg.buildSessionFactory().close())
        .isInstanceOf(SchemaManagementException.class)
        .hasMessageContaining("render_jobs");
  }

  /**
   * A Hibernate {@link Configuration} that validates (never mutates) the given schema on the shared
   * container, applying the same naming strategies Spring Boot uses when the application boots so
   * implicitly named columns are resolved identically.
   */
  private static Configuration validatingConfiguration(String schema) {
    Configuration cfg = new Configuration();
    cfg.setProperty("hibernate.connection.url", DB.getJdbcUrl());
    cfg.setProperty("hibernate.connection.username", DB.getUsername());
    cfg.setProperty("hibernate.connection.password", DB.getPassword());
    cfg.setProperty("hibernate.connection.driver_class", "org.postgresql.Driver");
    cfg.setProperty("hibernate.dialect", "org.hibernate.dialect.PostgreSQLDialect");
    cfg.setProperty("hibernate.hbm2ddl.auto", "validate");
    cfg.setProperty("hibernate.default_schema", schema);
    cfg.setProperty(
        "hibernate.physical_naming_strategy",
        "org.hibernate.boot.model.naming.CamelCaseToUnderscoresNamingStrategy");
    cfg.setProperty(
        "hibernate.implicit_naming_strategy",
        "org.springframework.boot.hibernate.SpringImplicitNamingStrategy");
    return cfg;
  }
}
