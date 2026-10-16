package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.flywaydb.core.api.MigrationVersion;
import org.flywaydb.core.api.configuration.FluentConfiguration;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;

class CpqV62MigrationTest {
  @Test
  void upgradesV61ThroughV66AndPreservesAppendOnlyComparisonBoundEvidence() {
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
      assertThat(upgraded.info().current().getVersion().toString()).isEqualTo("66");

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

  @Test void v66PreservesBothRealFailedBatchRowsAndScopesOnlyNewRequests() throws Exception {
    try(var database=new PostgreSQLContainer<>("postgres:17-alpine")) {
      database.start();flyway(database).target(MigrationVersion.fromVersion("65")).load().migrate();
      var json=new com.fasterxml.jackson.databind.ObjectMapper();var before=new java.util.ArrayList<String>();
      try(var connection=database.createConnection("")) {
        String[] roots={"cpq-first-real-ai-experiment-evidence","cpq-source-fidelity-completed-experiment-evidence"};
        for(String root:roots){var path=java.nio.file.Path.of("../docs",root);if(!java.nio.file.Files.exists(path))path=java.nio.file.Path.of("intelligence/docs",root);
          var row=json.readTree(java.nio.file.Files.readString(path.resolve("source-fidelity-durable-request.json")));var saved=json.readTree(java.nio.file.Files.readString(path.resolve("prepared-pilot.json")));
          try(var insert=connection.prepareStatement("INSERT INTO cpq_owner_pilots(pilot_id,owner_principal,policy_version,scope_sha256,snapshot,total_budget_usd) VALUES(CAST(? AS uuid),'TEST_FIXTURE_OWNER','OWNER_MACHINE_PILOT_V1',repeat('a',64),CAST(? AS jsonb),1)")){insert.setString(1,row.get("pilot_id").asText());insert.setString(2,saved.get("snapshot").toString());insert.executeUpdate();}
          try(var insert=connection.prepareStatement("INSERT INTO cpq_machine_requests(request_id,pilot_id,slot,idempotency_key,authorized_by,authorization_payload,input_sha256,state,reserved_usd,input,response,failure) VALUES(CAST(? AS uuid),CAST(? AS uuid),'SOURCE_FIDELITY',?,'TEST_FIXTURE_OWNER',CAST(? AS jsonb),?,'FAILED_OR_AMBIGUOUS',0.3,CAST(? AS jsonb),CAST(? AS jsonb),?)")){
            insert.setString(1,row.get("request_id").asText());insert.setString(2,row.get("pilot_id").asText());insert.setString(3,row.get("idempotency_key").asText());insert.setString(4,row.get("authorization_payload").toString());insert.setString(5,row.get("input_sha256").asText());insert.setString(6,row.get("input").toString());insert.setString(7,row.get("response").toString());insert.setString(8,row.get("failure").asText());insert.executeUpdate();}
        }
        try(var rows=connection.createStatement().executeQuery("SELECT to_jsonb(r)::text FROM cpq_machine_requests r ORDER BY request_id")){while(rows.next())before.add(rows.getString(1));}
      }
      flyway(database).load().migrate();
      try(var connection=database.createConnection("")){
        var after=new java.util.ArrayList<String>();try(var rows=connection.createStatement().executeQuery("SELECT (to_jsonb(r)-'subject_prompt_sha256')::text FROM cpq_machine_requests r ORDER BY request_id")){while(rows.next())after.add(rows.getString(1));}
        assertThat(after).isEqualTo(before);
        var stmt=connection.createStatement();String pilot="53e43e2c-8bfa-4798-8fad-30a068d97dac";
        String prefix="INSERT INTO cpq_machine_requests(request_id,pilot_id,slot,idempotency_key,authorized_by,authorization_payload,input_sha256,state,reserved_usd,input,subject_prompt_sha256) VALUES(gen_random_uuid(),'"+pilot+"',";
        stmt.execute(prefix+"'CRITIC_A','TEST_FIXTURE_CRITIC','fixture','{}',repeat('a',64),'AUTHORIZED',.1,'{}',NULL)");
        assertThatThrownBy(()->stmt.execute(prefix+"'CRITIC_A','TEST_FIXTURE_OTHER','fixture','{}',repeat('a',64),'AUTHORIZED',.1,'{}',NULL)")).hasMessageContaining("duplicate key");
        assertThatThrownBy(()->stmt.execute(prefix+"'CRITIC_B','TEST_FIXTURE_BAD_SCOPE','fixture','{}',repeat('a',64),'AUTHORIZED',.1,'{}',repeat('b',64))")).hasMessageContaining("cpq_source_subject_scope");
        assertThatThrownBy(()->stmt.execute("UPDATE cpq_owner_pilots SET snapshot='{}' WHERE pilot_id='"+pilot+"'")).hasMessageContaining("immutable");
      }
    }
  }

  private static FluentConfiguration flyway(PostgreSQLContainer<?> database) {
    return org.flywaydb.core.Flyway.configure()
        .dataSource(database.getJdbcUrl(), database.getUsername(), database.getPassword())
        .locations("classpath:db/migration");
  }
}
