package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest(
    classes = PublisherSupportFlywayConfigurationTest.ConsumerShapedApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:publisher_support_without_consumer_flyway;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=none",
      "spring.flyway.enabled=false",
      "spring.flyway.locations=classpath:db/migration",
      "publisher.support.flyway.enabled=true"
    })
class PublisherSupportWithoutConsumerFlywayTest {

  @Autowired private ApplicationContext applicationContext;
  @Autowired private JdbcTemplate jdbcTemplate;

  @Autowired
  @Qualifier("publisherSupportFlyway") private Flyway publisherSupportFlyway;

  @Test
  void supportFlywayStartsWhenConsumerFlywayIsDisabled() {
    assertThat(applicationContext.containsBean("flywayInitializer")).isFalse();
    assertThat(publisherSupportFlyway.getConfiguration().getDefaultSchema())
        .isEqualTo(PublisherSupportFlywayConfiguration.SCHEMA);
    assertThat(publisherSupportFlyway.getConfiguration().getTable())
        .isEqualTo(PublisherSupportFlywayConfiguration.HISTORY_TABLE);

    assertThat(tableCount(PublisherSupportFlywayConfiguration.SCHEMA, "PROVIDER_OPERATION_RECORDS"))
        .isOne();
    assertThat(
            tableCount(
                PublisherSupportFlywayConfiguration.SCHEMA,
                PublisherSupportFlywayConfiguration.HISTORY_TABLE))
        .isOne();
    assertThat(tableCount("PUBLIC", "CONSUMER_SERVICE_MARKER")).isZero();
  }

  private int tableCount(String schema, String table) {
    return jdbcTemplate.queryForObject(
        "select count(*) from information_schema.tables "
            + "where upper(table_schema) = upper(?) and upper(table_name) = upper(?)",
        Integer.class,
        schema,
        table);
  }
}
