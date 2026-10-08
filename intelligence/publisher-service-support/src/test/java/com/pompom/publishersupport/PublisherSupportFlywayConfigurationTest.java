package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest(
    classes = PublisherSupportFlywayConfigurationTest.ConsumerShapedApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:publisher_consumer_configuration;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=validate",
      "spring.flyway.enabled=true",
      "spring.flyway.locations=classpath:db/migration"
    })
class PublisherSupportFlywayConfigurationTest {

  @Autowired private JdbcTemplate jdbcTemplate;
  @Autowired private DataSource dataSource;

  @Autowired
  @Qualifier("publisherSupportFlyway") private Flyway publisherSupportFlyway;

  @Test
  void consumerV1AndSupportV1UseSeparateSchemasAndHistoryTables() {
    assertThat(dataSource).isNotNull();
    assertThat(publisherSupportFlyway.getConfiguration().getLocations())
        .anyMatch(
            location ->
                location
                    .getDescriptor()
                    .equals(PublisherSupportFlywayConfiguration.MIGRATION_LOCATION));
    assertThat(publisherSupportFlyway.getConfiguration().getDefaultSchema())
        .isEqualTo(PublisherSupportFlywayConfiguration.SCHEMA);
    assertThat(publisherSupportFlyway.getConfiguration().getTable())
        .isEqualTo(PublisherSupportFlywayConfiguration.HISTORY_TABLE);

    assertThat(tableCount("PUBLIC", "CONSUMER_SERVICE_MARKER")).isOne();
    assertThat(tableCount(PublisherSupportFlywayConfiguration.SCHEMA, "PROVIDER_OPERATION_RECORDS"))
        .isOne();
    assertThat(tableCount("PUBLIC", "FLYWAY_SCHEMA_HISTORY")).isOne();
    assertThat(
            tableCount(
                PublisherSupportFlywayConfiguration.SCHEMA,
                PublisherSupportFlywayConfiguration.HISTORY_TABLE))
        .isOne();
  }

  private int tableCount(String schema, String table) {
    return jdbcTemplate.queryForObject(
        "select count(*) from information_schema.tables "
            + "where upper(table_schema) = upper(?) and upper(table_name) = upper(?)",
        Integer.class,
        schema,
        table);
  }

  @SpringBootConfiguration
  @EnableAutoConfiguration
  static class ConsumerShapedApplication {}
}
