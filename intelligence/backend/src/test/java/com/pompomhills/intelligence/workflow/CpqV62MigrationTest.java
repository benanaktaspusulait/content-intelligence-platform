package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.flywaydb.core.api.MigrationVersion;
import org.flywaydb.core.api.configuration.FluentConfiguration;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;

class CpqV62MigrationTest {
  @Test
  void upgradesV61ThroughV63AndPreservesAppendOnlyComparisonBoundEvidence() {
    try (var database = new PostgreSQLContainer<>("postgres:17-alpine")
        .withDatabaseName("pompom")
        .withUsername("pompom")
        .withPassword("pompom_test")) {
      database.start();

      var version61 = flyway(database).target(MigrationVersion.fromVersion("61")).load();
      version61.migrate();
      assertThat(version61.info().current().getVersion().toString()).isEqualTo("61");

      var upgraded = flyway(database).load();
      upgraded.migrate();
      assertThat(upgraded.info().current().getVersion().toString()).isEqualTo("63");

      try (var connection = database.createConnection("")) {
        var statement = connection.createStatement();
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
