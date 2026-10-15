package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.flywaydb.core.api.MigrationVersion;
import org.flywaydb.core.api.configuration.FluentConfiguration;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;

class CpqV62MigrationTest {
  @Test
  void upgradesV61ThroughV64AndPreservesAppendOnlyComparisonBoundEvidence() {
    try (var database = new PostgreSQLContainer<>("postgres:17-alpine")
        .withDatabaseName("pompom")
        .withUsername("pompom")
        .withPassword("pompom_test")) {
      database.start();

      var version61 = flyway(database).target(MigrationVersion.fromVersion("61")).load();
      version61.migrate();
      assertThat(version61.info().current().getVersion().toString()).isEqualTo("61");

      flyway(database).target(MigrationVersion.fromVersion("63")).load().migrate();
      try (var connection = database.createConnection("")) {
        var statement = connection.createStatement();
        statement.execute("INSERT INTO contents(id,title,type) VALUES (11,'Legacy fidelity fixture','SHORT')");
        statement.execute("INSERT INTO prompt_versions(id,content_id,version_number,raw_text) VALUES (11,11,1,'Legacy source')");
        statement.execute("INSERT INTO post_family_workflow_events(id,kind,payload) VALUES ('00000000-0000-0000-0000-000000000062','REVIEW','{}')");
        statement.execute("INSERT INTO cpq_fidelity_reviews(content_id,prompt_version_id,approved_story_id,approved_revision,approved_story_fingerprint,original_prompt_fingerprint,candidate_prompt_fingerprint,intervention_fingerprint,changed_beat_ids,source_event_mapping,analysis_id,ruleset_version,cpq_rubric_version,production_settings_fingerprint,reviewer_principal,reviewer_authority,review_method_version,citations,rationale,decision,valid_until) VALUES(11,11,'legacy-story','legacy-revision',repeat('c',64),repeat('a',64),repeat('b',64),repeat('d',64),'[]','[]','00000000-0000-0000-0000-000000000062','1.11','creative-prompt-quality-v1',repeat('e',64),'legacy-fixture','EVIDENCE_REVIEWER','human-source-fidelity-v1','[]','Frozen legacy rationale must remain unchanged.','UNKNOWN',now()+interval '1 day')");
      }
      var upgraded = flyway(database).load();
      upgraded.migrate();
      assertThat(upgraded.info().current().getVersion().toString()).isEqualTo("64");

      try (var connection = database.createConnection("")) {
        var statement = connection.createStatement();
        try (var rows = statement.executeQuery("SELECT subject_type,original_subject_id,decision,rationale,approved_revision,candidate_prompt_fingerprint FROM cpq_fidelity_reviews WHERE prompt_version_id=11")) {
          rows.next(); assertThat(rows.getString(1)).isEqualTo("OPTIMIZATION_CANDIDATE"); assertThat(rows.getObject(2)).isNull();
          assertThat(rows.getString(3)).isEqualTo("UNKNOWN"); assertThat(rows.getString(4)).isEqualTo("Frozen legacy rationale must remain unchanged.");
          assertThat(rows.getString(5)).isEqualTo("legacy-revision"); assertThat(rows.getString(6)).isEqualTo("b".repeat(64));
        }
        statement.execute("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES ('00000000-0000-0000-0000-000000000061','REVIEW',NULL,'{}')");
        statement.execute("INSERT INTO post_family_workflow_events(id,kind,binding_sha256,payload) VALUES ('00000000-0000-0000-0000-000000000063','CREATIVE_OPTIMIZATION',NULL,'{}')");
        statement.execute("INSERT INTO contents(id,title,type) VALUES (10,'CPQ migration test','SHORT')");
        statement.execute("INSERT INTO prompt_versions(id,content_id,version_number,raw_text) VALUES (10,10,1,'Mimi prompt')");
        statement.execute("INSERT INTO cpq_assessments(analysis_id,comparison_id,content_id,prompt_version_id,candidate_id,original_prompt_fingerprint,candidate_prompt_fingerprint,ruleset_version,rubric_version,result) VALUES ('00000000-0000-0000-0000-000000000061','00000000-0000-0000-0000-000000000063',10,10,'candidate-a',repeat('a',64),repeat('b',64),'1.11','creative-prompt-quality-v1','{}'),('00000000-0000-0000-0000-000000000061','00000000-0000-0000-0000-000000000063',10,10,'candidate-a',repeat('a',64),repeat('b',64),'1.11','creative-prompt-quality-v1','{}')");
        try (var rows = statement.executeQuery("SELECT count(*) FROM cpq_assessments WHERE candidate_id='candidate-a'")) {
          rows.next();
          assertThat(rows.getInt(1)).isEqualTo(2);
        }
        try (var rows = statement.executeQuery("SELECT comparison_id FROM cpq_assessments WHERE candidate_id='candidate-a' LIMIT 1")) {
          rows.next(); assertThat(rows.getString(1)).isEqualTo("00000000-0000-0000-0000-000000000063");
        }
        assertThatThrownBy(() -> statement.executeUpdate("UPDATE cpq_assessments SET result='{}' WHERE candidate_id='candidate-a'"))
            .hasMessageContaining("immutable");
        assertThatThrownBy(() -> statement.executeUpdate("DELETE FROM cpq_assessments WHERE candidate_id='candidate-a'"))
            .hasMessageContaining("immutable");
        assertThatThrownBy(() -> statement.executeUpdate("INSERT INTO cpq_assessments(analysis_id,content_id,prompt_version_id,candidate_id,original_prompt_fingerprint,candidate_prompt_fingerprint,ruleset_version,rubric_version,fidelity_evidence_id,result) VALUES ('00000000-0000-0000-0000-000000000061',10,10,'bad-binding',repeat('a',64),repeat('b',64),'1.11','creative-prompt-quality-v1','00000000-0000-0000-0000-000000000000','{}')"))
            .isInstanceOf(java.sql.SQLException.class);
      }
    } catch (java.sql.SQLException exception) {
      throw new AssertionError(exception);
    }
  }

  private static FluentConfiguration flyway(PostgreSQLContainer<?> database) {
    return org.flywaydb.core.Flyway.configure()
        .dataSource(database.getJdbcUrl(), database.getUsername(), database.getPassword())
        .locations("classpath:db/migration");
  }
}
