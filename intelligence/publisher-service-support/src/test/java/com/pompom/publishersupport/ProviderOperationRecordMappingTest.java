package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Table;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class ProviderOperationRecordMappingTest {

  @Test
  void mapsTheProviderOperationTableIntoTheOwnedSupportSchema() {
    Table table = ProviderOperationRecord.class.getAnnotation(Table.class);

    assertThat(table.name()).isEqualTo("provider_operation_records");
    assertThat(table.schema()).isEqualTo(PublisherSupportFlywayConfiguration.SCHEMA);
    assertThat(table.uniqueConstraints())
        .anySatisfy(
            uniqueConstraint ->
                assertThat(uniqueConstraint.columnNames())
                    .containsExactly("command_idempotency_key"));
    assertThat(ProviderOperationRecord.class.getDeclaredFields())
        .noneMatch(field -> field.getName().toLowerCase().contains("token"));
    assertThat(ProviderOperationRecord.class.getDeclaredFields())
        .noneMatch(field -> field.getName().toLowerCase().contains("rawresponse"));
  }

  @Test
  void convertersPersistContractWireValuesInsteadOfJavaEnumNames() {
    ProviderOperationRecord.PublishStatusConverter statusConverter =
        new ProviderOperationRecord.PublishStatusConverter();
    ProviderOperationRecord.PublishErrorClassConverter errorConverter =
        new ProviderOperationRecord.PublishErrorClassConverter();

    assertThat(statusConverter.convertToDatabaseColumn(PublishStatus.RECONCILIATION_REQUIRED))
        .isEqualTo("reconciliation_required");
    assertThat(statusConverter.convertToEntityAttribute("completed"))
        .isEqualTo(PublishStatus.COMPLETED);
    assertThat(errorConverter.convertToDatabaseColumn(PublishErrorClass.RATE_LIMITED))
        .isEqualTo("rate_limited");
    assertThat(errorConverter.convertToEntityAttribute("duplicate"))
        .isEqualTo(PublishErrorClass.DUPLICATE);
  }

  @Test
  void migrationUsesTheExplicitSupportLocationAndSchemaWithoutConsumerHistoryCollision()
      throws IOException {
    assertThat(PublisherSupportFlywayConfiguration.MIGRATION_LOCATION)
        .isEqualTo("classpath:db/publisher-support-migration");
    assertThat(PublisherSupportFlywayConfiguration.SCHEMA).isEqualTo("publisher_support");
    assertThat(PublisherSupportFlywayConfiguration.HISTORY_TABLE)
        .isEqualTo("publisher_support_schema_history");

    String migration = readMigration();

    assertThat(migration)
        .contains("CREATE SCHEMA IF NOT EXISTS publisher_support")
        .contains("CREATE TABLE publisher_support.provider_operation_records")
        .contains("command_idempotency_key")
        .contains("provider_request_id")
        .contains("command_fingerprint")
        .contains("reconciliation_required")
        .contains("uq_provider_operation_command_idempotency_key")
        .contains("idx_provider_operation_reconciliation");
    assertThat(migration).doesNotContain("access_token", "refresh_token", "raw_provider_response");
    assertThat(migration).doesNotContain("REFERENCES publication_attempts");
  }

  @Test
  void explicitlyMapsTheRequiredOperationColumns() {
    assertThat(column("commandIdempotencyKey").name()).isEqualTo("command_idempotency_key");
    assertThat(column("providerRequestId").name()).isEqualTo("provider_request_id");
    assertThat(column("commandFingerprint").name()).isEqualTo("command_fingerprint");
    assertThat(column("reconciliationRequired").name()).isEqualTo("reconciliation_required");
    assertThat(column("startedAt").name()).isEqualTo("started_at");
    assertThat(column("completedAt").name()).isEqualTo("completed_at");
  }

  private Column column(String name) {
    try {
      return ProviderOperationRecord.class.getDeclaredField(name).getAnnotation(Column.class);
    } catch (ReflectiveOperationException exception) {
      throw new AssertionError(exception);
    }
  }

  private String readMigration() throws IOException {
    try (InputStream input =
        getClass()
            .getResourceAsStream(
                "/db/publisher-support-migration/V1__create_provider_operation_records.sql")) {
      if (input == null) {
        throw new AssertionError("provider operation migration is missing");
      }
      return new String(input.readAllBytes(), StandardCharsets.UTF_8);
    }
  }
}
