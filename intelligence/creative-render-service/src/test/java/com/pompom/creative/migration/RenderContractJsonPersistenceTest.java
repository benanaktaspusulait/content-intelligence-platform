package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.domain.OpenArtCreditLog;
import org.hibernate.SessionFactory;
import org.hibernate.boot.MetadataSources;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/** Verifies real PostgreSQL JSON binding after migrations, rather than H2's permissive coercion. */
@Testcontainers(disabledWithoutDocker = true)
class RenderContractJsonPersistenceTest {
  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  @Test
  void storesContractAndConstraintsAsQueryableJsonObjects() throws Exception {
    RenderMigrationSupport.migrate(DB);
    var registry = new StandardServiceRegistryBuilder()
        .applySetting("hibernate.connection.url", DB.getJdbcUrl())
        .applySetting("hibernate.connection.username", DB.getUsername())
        .applySetting("hibernate.connection.password", DB.getPassword())
        .applySetting("hibernate.default_schema", "creative_render")
        .build();
    try (SessionFactory factory = new MetadataSources(registry)
        .addAnnotatedClass(RenderJob.class).addAnnotatedClass(OpenArtCreditLog.class).buildMetadata().buildSessionFactory()) {
      var job = RenderJob.builder().contentId(1L).promptVersionId(2L)
          .contentTitleSnapshot("LOCAL_MOCK JSON persistence").promptVersionNumberSnapshot(1)
          .jobType(RenderJob.JobType.VIDEO).openartModel("LOCAL_MOCK")
          .promptTextSnapshot("Local fixture").promptSha256("a".repeat(64))
          .creativeContractSnapshot("{\"intent\":{\"text\":\"Luca pushes.\"}}")
          .compiledGenerationConstraints("{\"durationSeconds\":6,\"constraints\":[\"preserve intent\"]}")
          .openartParams("{\"aspectRatio\":\"9:16\"}").build();
      try (var session = factory.openSession()) {
        var transaction = session.beginTransaction();
        session.persist(job);
        session.persist(OpenArtCreditLog.builder().renderJob(job).operation("ESTIMATE")
            .operationMetadata("{\"source\":\"LOCAL_MOCK\"}").build());
        session.persist(OpenArtCreditLog.builder().renderJob(job).operation("RESERVATION")
            .operationMetadata(null).build());
        transaction.commit();
      }
      try (var session = factory.openSession()) {
        var loaded = session.find(RenderJob.class, job.getId());
        assertThat(loaded.getCreativeContractSnapshot()).contains("Luca pushes.");
        assertThat(loaded.getCompiledGenerationConstraints()).contains("preserve intent");
        session.doWork(connection -> {
          try (var credits = connection.createStatement();
              var rows = credits.executeQuery("SELECT operation_metadata->>'source' FROM creative_render.openart_credit_log WHERE operation='ESTIMATE'")) {
            assertThat(rows.next()).isTrue();
            assertThat(rows.getString(1)).isEqualTo("LOCAL_MOCK");
          }
          try (var statement = connection.prepareStatement(
              "SELECT creative_contract_snapshot->'intent'->>'text', "
                  + "compiled_generation_constraints->>'durationSeconds', "
                  + "jsonb_typeof(compiled_generation_constraints) FROM creative_render.render_jobs WHERE id=?")) {
            statement.setObject(1, job.getId());
            try (var row = statement.executeQuery()) {
              assertThat(row.next()).isTrue();
              assertThat(row.getString(1)).isEqualTo("Luca pushes.");
              assertThat(row.getString(2)).isEqualTo("6");
              assertThat(row.getString(3)).isEqualTo("object");
            }
          }
        });
      }
    } finally {
      StandardServiceRegistryBuilder.destroy(registry);
    }
  }
}
