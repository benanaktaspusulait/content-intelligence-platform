package com.pompom.creative.migration;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.Statement;
import java.util.Map;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Verifies the guarded, non-destructive legacy copy (V2). Representative legacy render data is
 * seeded into the backend-owned {@code public} schema, the render migrations run, and we assert the
 * copy preserved identities, counts, status distribution and prompt SHA-256 snapshots, is
 * idempotent, and never mutated the public source rows.
 */
@Testcontainers(disabledWithoutDocker = true)
class LegacyDataCopyMigrationTest {

  @Container static final PostgreSQLContainer<?> DB = RenderMigrationSupport.newContainer();

  // Deterministic ids used in both the public seed and the copy assertions.
  private static final String JOB_A = "11111111-1111-1111-1111-111111111111";
  private static final String JOB_B = "22222222-2222-2222-2222-222222222222";
  private static final String JOB_C = "33333333-3333-3333-3333-333333333333";
  private static final String ASSET_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
  private static final String QA_A = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
  private static final String CREDIT_1 = "cccccccc-cccc-cccc-cccc-cccccccccccc";
  private static final String CREDIT_2 = "dddddddd-dddd-dddd-dddd-dddddddddddd";

  private static final String PROMPT_ONE = "PROMPT ONE: Kiko bounces in Central Square";
  private static final String PROMPT_TWO = "PROMPT TWO: Mimi watches the sunset over Pompom Hills";

  @BeforeAll
  static void seedLegacyThenMigrate() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB);
        Statement st = c.createStatement()) {
      st.execute(
          """
          CREATE TABLE public.contents (
            id BIGINT PRIMARY KEY,
            title VARCHAR(255) NOT NULL
          );
          CREATE TABLE public.prompt_versions (
            id BIGINT PRIMARY KEY,
            content_id BIGINT NOT NULL REFERENCES public.contents(id),
            version_number INT NOT NULL,
            raw_text TEXT NOT NULL
          );
          CREATE TABLE public.render_jobs (
            id UUID PRIMARY KEY,
            content_id BIGINT NOT NULL REFERENCES public.contents(id),
            prompt_version_id BIGINT NOT NULL REFERENCES public.prompt_versions(id),
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
          CREATE TABLE public.render_assets (
            id UUID PRIMARY KEY,
            render_job_id UUID NOT NULL REFERENCES public.render_jobs(id),
            content_id BIGINT NOT NULL REFERENCES public.contents(id),
            asset_type VARCHAR(20) NOT NULL,
            relative_path TEXT NOT NULL,
            file_size_bytes BIGINT NOT NULL,
            duration_ms INT,
            width INT NOT NULL,
            height INT NOT NULL,
            frame_rate NUMERIC(5,2),
            codec VARCHAR(50),
            download_url TEXT,
            downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_current BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            entity_version INT NOT NULL DEFAULT 1
          );
          CREATE TABLE public.render_qa_results (
            id UUID PRIMARY KEY,
            render_asset_id UUID NOT NULL REFERENCES public.render_assets(id),
            prompt_version_id BIGINT NOT NULL REFERENCES public.prompt_versions(id),
            decision VARCHAR(30) NOT NULL,
            decision_reason TEXT NOT NULL,
            confidence NUMERIC(3,2),
            compliance_score INT NOT NULL,
            compliance_issues JSONB,
            has_dead_air BOOLEAN NOT NULL,
            dead_air_segments JSONB,
            character_identity_verified BOOLEAN NOT NULL,
            character_identity_issues TEXT,
            physics_consistent BOOLEAN NOT NULL,
            physics_violations TEXT,
            has_object_duplication BOOLEAN NOT NULL,
            duplication_details TEXT,
            final_execution_score INT,
            final_execution_issues TEXT,
            requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
            human_reviewed_at TIMESTAMPTZ,
            human_reviewer VARCHAR(50),
            human_decision VARCHAR(30),
            human_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            entity_version INT NOT NULL DEFAULT 1
          );
          CREATE TABLE public.openart_credit_log (
            id UUID PRIMARY KEY,
            render_job_id UUID REFERENCES public.render_jobs(id),
            operation VARCHAR(50) NOT NULL,
            operation_metadata JSONB,
            credits_before NUMERIC(10,2),
            credits_spent NUMERIC(10,2) NOT NULL DEFAULT 0,
            credits_after NUMERIC(10,2),
            logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
          );
          """);

      st.execute(
          "INSERT INTO public.contents(id,title) VALUES " + "(1,'Episode One'),(2,'Episode Two')");
      st.execute(
          "INSERT INTO public.prompt_versions(id,content_id,version_number,raw_text) VALUES "
              + "(10,1,1,'"
              + PROMPT_ONE
              + "'),(20,2,3,'"
              + PROMPT_TWO
              + "')");
      st.execute(
          "INSERT INTO public.render_jobs(id,content_id,prompt_version_id,job_type,openart_model,status) VALUES "
              + "('"
              + JOB_A
              + "',1,10,'VIDEO','seedance-1.0','COMPLETE'),"
              + "('"
              + JOB_B
              + "',1,10,'FIRST_FRAME','nano-banana','FAILED'),"
              + "('"
              + JOB_C
              + "',2,20,'VIDEO','seedance-1.0','QUEUED')");
      st.execute(
          "INSERT INTO public.render_assets(id,render_job_id,content_id,asset_type,relative_path,file_size_bytes,width,height) VALUES "
              + "('"
              + ASSET_A
              + "','"
              + JOB_A
              + "',1,'VIDEO','renders/1/video-v1.mp4',123456,1920,1080)");
      st.execute(
          "INSERT INTO public.render_qa_results(id,render_asset_id,prompt_version_id,decision,decision_reason,compliance_score,has_dead_air,character_identity_verified,physics_consistent,has_object_duplication) VALUES "
              + "('"
              + QA_A
              + "','"
              + ASSET_A
              + "',10,'ACCEPT','looks good',92,false,true,true,false)");
      st.execute(
          "INSERT INTO public.openart_credit_log(id,render_job_id,operation,credits_spent) VALUES "
              + "('"
              + CREDIT_1
              + "','"
              + JOB_A
              + "','VIDEO_GENERATION',4.50),"
              + "('"
              + CREDIT_2
              + "','"
              + JOB_A
              + "','FIRST_FRAME_GENERATION',1.25)");
    }

    RenderMigrationSupport.migrate(DB);
  }

  @Test
  void copiesRenderJobsPreservingIdentityCountAndStatusDistribution() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(RenderMigrationSupport.count(c, "creative_render.render_jobs")).isEqualTo(3);

      assertThat(RenderMigrationSupport.idSet(c, "creative_render.render_jobs"))
          .containsExactlyInAnyOrder(JOB_A, JOB_B, JOB_C);

      Map<String, Long> publicDist =
          RenderMigrationSupport.statusDistribution(c, "public.render_jobs");
      Map<String, Long> renderDist =
          RenderMigrationSupport.statusDistribution(c, "creative_render.render_jobs");
      assertThat(renderDist).isEqualTo(publicDist);
      assertThat(renderDist)
          .containsEntry("COMPLETE", 1L)
          .containsEntry("FAILED", 1L)
          .containsEntry("QUEUED", 1L);
    }
  }

  @Test
  void materializesImmutablePromptSnapshotsWithSha256() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT content_title_snapshot FROM creative_render.render_jobs WHERE id='"
                      + JOB_A
                      + "'"))
          .isEqualTo("Episode One");
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT prompt_version_number_snapshot::text FROM creative_render.render_jobs WHERE id='"
                      + JOB_A
                      + "'"))
          .isEqualTo("1");
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT prompt_text_snapshot FROM creative_render.render_jobs WHERE id='"
                      + JOB_A
                      + "'"))
          .isEqualTo(PROMPT_ONE);
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT prompt_sha256 FROM creative_render.render_jobs WHERE id='" + JOB_A + "'"))
          .isEqualTo(sha256Hex(PROMPT_ONE));

      // A second content/prompt to prove the join resolves per-row, not by accident.
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT content_title_snapshot FROM creative_render.render_jobs WHERE id='"
                      + JOB_C
                      + "'"))
          .isEqualTo("Episode Two");
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT prompt_sha256 FROM creative_render.render_jobs WHERE id='" + JOB_C + "'"))
          .isEqualTo(sha256Hex(PROMPT_TWO));
    }
  }

  @Test
  void copiesDependentRenderTables() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(RenderMigrationSupport.count(c, "creative_render.render_assets")).isEqualTo(1);
      assertThat(RenderMigrationSupport.idSet(c, "creative_render.render_assets"))
          .containsExactly(ASSET_A);

      assertThat(RenderMigrationSupport.count(c, "creative_render.render_qa_results")).isEqualTo(1);
      assertThat(RenderMigrationSupport.idSet(c, "creative_render.render_qa_results"))
          .containsExactly(QA_A);

      assertThat(RenderMigrationSupport.count(c, "creative_render.openart_credit_log"))
          .isEqualTo(2);
      // credits_used is a new not-null column; the copy backfills it from the legacy credits_spent.
      assertThat(
              RenderMigrationSupport.scalarString(
                  c,
                  "SELECT credits_used::text FROM creative_render.openart_credit_log WHERE id='"
                      + CREDIT_1
                      + "'"))
          .isEqualTo("4.50");
    }
  }

  @Test
  void copyIsIdempotentWhenReExecuted() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      long before = RenderMigrationSupport.count(c, "creative_render.render_jobs");

      // Re-run the copy+verify migration body; ON CONFLICT DO NOTHING must prevent duplicates.
      RenderMigrationSupport.execClasspathScript(
          c, "/db/migration/V2__copy_and_verify_legacy_creative_data.sql");

      assertThat(RenderMigrationSupport.count(c, "creative_render.render_jobs")).isEqualTo(before);
      assertThat(RenderMigrationSupport.count(c, "creative_render.render_assets")).isEqualTo(1);
      assertThat(RenderMigrationSupport.count(c, "creative_render.render_qa_results")).isEqualTo(1);
      assertThat(RenderMigrationSupport.count(c, "creative_render.openart_credit_log"))
          .isEqualTo(2);
    }
  }

  @Test
  void leavesPublicSourceRowsUnchanged() throws Exception {
    try (Connection c = RenderMigrationSupport.connect(DB)) {
      assertThat(RenderMigrationSupport.count(c, "public.render_jobs")).isEqualTo(3);
      assertThat(RenderMigrationSupport.count(c, "public.render_assets")).isEqualTo(1);
      assertThat(RenderMigrationSupport.count(c, "public.render_qa_results")).isEqualTo(1);
      assertThat(RenderMigrationSupport.count(c, "public.openart_credit_log")).isEqualTo(2);
      assertThat(RenderMigrationSupport.count(c, "public.contents")).isEqualTo(2);
      assertThat(RenderMigrationSupport.count(c, "public.prompt_versions")).isEqualTo(2);

      // The public render_jobs still carries no snapshot columns (never altered by the render
      // side).
      assertThat(
              RenderMigrationSupport.tableNames(DB, "public").contains("render_jobs")
                  && !publicHasColumn(c, "render_jobs", "prompt_sha256"))
          .as("render migrations must not add snapshot columns to public.render_jobs")
          .isTrue();
    }
  }

  private static boolean publicHasColumn(Connection c, String table, String column)
      throws Exception {
    try (Statement st = c.createStatement();
        var rs =
            st.executeQuery(
                "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='"
                    + table
                    + "' AND column_name='"
                    + column
                    + "'")) {
      return rs.next();
    }
  }

  private static String sha256Hex(String value) throws Exception {
    MessageDigest md = MessageDigest.getInstance("SHA-256");
    byte[] digest = md.digest(value.getBytes(StandardCharsets.UTF_8));
    StringBuilder sb = new StringBuilder(digest.length * 2);
    for (byte b : digest) {
      sb.append(Character.forDigit((b >> 4) & 0xF, 16));
      sb.append(Character.forDigit(b & 0xF, 16));
    }
    return sb.toString();
  }
}
