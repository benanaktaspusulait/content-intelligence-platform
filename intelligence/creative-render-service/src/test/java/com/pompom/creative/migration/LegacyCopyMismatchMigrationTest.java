package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import org.flywaydb.core.api.FlywayException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Exercises the V2 verification guard (the {@code RAISE EXCEPTION} on a count/id-set mismatch),
 * which the happy-path tests never trigger.
 *
 * <p>Legacy {@code public} render data is seeded such that one {@code render_jobs} row references a
 * {@code prompt_version_id} that does not exist. V2 copies via an inner join to {@code
 * public.prompt_versions}/{@code public.contents}, so that orphan row is silently dropped and the
 * render-side count diverges from the source. The migration must then RAISE, Flyway must abort, and
 * because the whole migration runs in one transaction nothing may be left behind: in particular
 * {@code creative_render.legacy_copy_audit} must not contain a falsely-recorded {@code VERIFIED}
 * row for {@code render_jobs}.
 */
@Testcontainers(disabledWithoutDocker = true)
class LegacyCopyMismatchMigrationTest {

  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  private static final String JOB_OK = "11111111-1111-1111-1111-111111111111";
  private static final String JOB_ORPHAN = "22222222-2222-2222-2222-222222222222";

  private static Throwable thrown;

  @BeforeAll
  static void seedMismatchedLegacyThenMigrate() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB);
        Statement st = c.createStatement()) {
      // Minimal public source tables. No foreign keys, so an orphan render_jobs row (pointing at a
      // non-existent prompt version) can be inserted -- the realistic data-integrity gap this guard
      // exists to catch.
      st.execute(
          """
          CREATE TABLE public.contents (
            id BIGINT PRIMARY KEY,
            title VARCHAR(255) NOT NULL
          );
          CREATE TABLE public.prompt_versions (
            id BIGINT PRIMARY KEY,
            content_id BIGINT NOT NULL,
            version_number INT NOT NULL,
            raw_text TEXT NOT NULL
          );
          CREATE TABLE public.render_jobs (
            id UUID PRIMARY KEY,
            content_id BIGINT NOT NULL,
            prompt_version_id BIGINT NOT NULL,
            job_type VARCHAR(20) NOT NULL,
            openart_job_id VARCHAR(100),
            openart_model VARCHAR(50) NOT NULL,
            openart_params JSONB,
            status VARCHAR(30) NOT NULL,
            attempt_number INT NOT NULL DEFAULT 1,
            max_attempts INT NOT NULL DEFAULT 3,
            credits_estimated NUMERIC(10,2),
            credits_actual NUMERIC(10,2),
            queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            failed_at TIMESTAMPTZ,
            error_code VARCHAR(50),
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            entity_version INT NOT NULL DEFAULT 1
          );
          """);

      st.execute("INSERT INTO public.contents(id,title) VALUES (1,'Episode One')");
      st.execute(
          "INSERT INTO public.prompt_versions(id,content_id,version_number,raw_text) VALUES "
              + "(10,1,1,'PROMPT ONE')");
      st.execute(
          "INSERT INTO public.render_jobs(id,content_id,prompt_version_id,job_type,openart_model,status) VALUES "
              + "('"
              + JOB_OK
              + "',1,10,'VIDEO','seedance-1.0','COMPLETE'),"
              // Orphan: prompt_version_id 999 has no matching prompt_versions row, so the copy's
              // inner join drops it -> target count (1) < source count (2) -> RAISE.
              + "('"
              + JOB_ORPHAN
              + "',1,999,'VIDEO','seedance-1.0','QUEUED')");
    }

    thrown =
        org.assertj.core.api.Assertions.catchThrowable(() -> RenderMigrationSupport.migrate(DB));
  }

  @Test
  void migrationAbortsWithTheVerificationExceptionOnACountMismatch() {
    assertThatThrownBy(
            () -> {
              if (thrown != null) {
                throw thrown;
              }
            })
        .isInstanceOf(FlywayException.class)
        .hasStackTraceContaining("render_jobs count mismatch");
  }

  @Test
  void leavesNoFalselyVerifiedAuditRowForRenderJobs() throws Exception {
    // V1 committed before V2, so the audit table exists; V2 rolled back, so it must be empty and in
    // particular carry no VERIFIED render_jobs row.
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(auditRowCount(c, "render_jobs", "VERIFIED")).isZero();
      assertThat(RenderMigrationSupport.count(c, "creative_render.legacy_copy_audit")).isZero();
    }
  }

  @Test
  void doesNotCommitAPartialRenderJobsCopy() throws Exception {
    // The aborted, transactional migration must not leave the single joinable row behind either.
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(RenderMigrationSupport.count(c, "creative_render.render_jobs")).isZero();
    }
  }

  @Test
  void leavesPublicSourceRowsUnchanged() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(RenderMigrationSupport.count(c, "public.render_jobs")).isEqualTo(2);
      assertThat(RenderMigrationSupport.count(c, "public.contents")).isEqualTo(1);
      assertThat(RenderMigrationSupport.count(c, "public.prompt_versions")).isEqualTo(1);
    }
  }

  private static long auditRowCount(Connection c, String sourceTable, String status)
      throws Exception {
    try (Statement st = c.createStatement();
        ResultSet rs =
            st.executeQuery(
                "SELECT count(*) FROM creative_render.legacy_copy_audit WHERE source_table='"
                    + sourceTable
                    + "' AND status='"
                    + status
                    + "'")) {
      rs.next();
      return rs.getLong(1);
    }
  }
}
