package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(
    classes = ProviderOperationRepositoryTest.TestApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:publisher_support;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=validate",
      "spring.flyway.enabled=true",
      "spring.flyway.locations=classpath:db/migration"
    })
class ProviderOperationRepositoryTest {

  @Autowired private ProviderOperationRepository repository;

  @Test
  void duplicateCommandsReturnThePersistedResultWithoutASecondProviderPost() {
    PublishCommand command = command("same-command");
    PublishResult completed = completedResult();
    AtomicInteger providerPosts = new AtomicInteger();

    ProviderOperationRepository.OperationClaim first = repository.claim(command);
    if (first.newOperation()) {
      providerPosts.incrementAndGet();
      repository.recordResult(command.idempotencyKey(), completed);
    }

    ProviderOperationRepository.OperationClaim duplicate = repository.claim(command);
    if (duplicate.newOperation()) {
      providerPosts.incrementAndGet();
      repository.recordResult(command.idempotencyKey(), completed);
    }

    assertThat(providerPosts).hasValue(1);
    assertThat(duplicate.newOperation()).isFalse();
    assertThat(duplicate.operation().getId()).isEqualTo(first.operation().getId());
    assertThat(duplicate.existingResult()).contains(completed);
  }

  @Test
  void recordsProviderIdsErrorStateAndReconciliationWithoutRawProviderPayload() {
    PublishCommand command = command("reconciliation-command");
    repository.claim(command, Instant.parse("2026-10-07T12:00:00Z"));
    PublishResult result =
        new PublishResult(
            PublishStatus.RECONCILIATION_REQUIRED,
            "post-id",
            "video-id",
            "https://provider.example/post-id",
            "request-id",
            PublishErrorClass.TRANSIENT.wireValue(),
            "Bearer secret-value provider response",
            true);

    ProviderOperationRecord saved = repository.recordResult(command.idempotencyKey(), result);

    assertThat(saved.getProviderRequestId()).isEqualTo("request-id");
    assertThat(saved.getProviderPostId()).isEqualTo("post-id");
    assertThat(saved.getProviderVideoId()).isEqualTo("video-id");
    assertThat(saved.getStatus()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(saved.getErrorClass()).isEqualTo(PublishErrorClass.TRANSIENT);
    assertThat(saved.isReconciliationRequired()).isTrue();
    assertThat(saved.getMessage()).doesNotContain("secret-value").contains("[REDACTED]");
    assertThat(saved.getStartedAt()).isEqualTo(Instant.parse("2026-10-07T12:00:00Z"));
    assertThat(saved.getCompletedAt()).isNotNull();
  }

  @Test
  void rejectsNullStatusResultsAtThePersistenceBoundary() {
    PublishCommand command = command("null-status-command");
    repository.claim(command);
    PublishResult invalid = new PublishResult(null, null, null, null, null, null, "invalid", false);

    assertThatThrownBy(() -> repository.recordResult(command.idempotencyKey(), invalid))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("status");
    assertThat(
            repository
                .findByCommandIdempotencyKey(command.idempotencyKey())
                .orElseThrow()
                .getStatus())
        .isNull();
  }

  @Test
  void doesNotOverwriteACompletedOperationWithALateResult() {
    PublishCommand command = command("terminal-command");
    repository.claim(command);
    PublishResult completed = completedResult();
    repository.recordResult(command.idempotencyKey(), completed);
    PublishResult lateFailure =
        new PublishResult(
            PublishStatus.FAILED,
            null,
            null,
            null,
            "late-request-id",
            PublishErrorClass.PROVIDER_REJECTED.wireValue(),
            "late failure",
            false);

    assertThatThrownBy(() -> repository.recordResult(command.idempotencyKey(), lateFailure))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("terminal");
    assertThat(repository.findExistingResult(command.idempotencyKey())).contains(completed);
  }

  @Test
  void rejectsProviderIdentifiersBeyondThePersistedColumnBound() {
    PublishCommand command = command("identifier-bound-command");
    repository.claim(command);
    PublishResult oversized =
        new PublishResult(
            PublishStatus.COMPLETED,
            "p".repeat(ProviderOperationRecord.MAX_IDENTIFIER_LENGTH + 1),
            "video-id",
            null,
            "request-id",
            null,
            "completed",
            false);

    assertThatThrownBy(() -> repository.recordResult(command.idempotencyKey(), oversized))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("providerPostId");
  }

  @SpringBootConfiguration
  @EnableAutoConfiguration
  static class TestApplication {}

  private PublishCommand command(String idempotencyKey) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        idempotencyKey,
        "account-id",
        "immutable-asset-reference",
        "a".repeat(64),
        "title",
        "caption",
        List.of("shorts"),
        false,
        Map.of("privacy", "private"));
  }

  private PublishResult completedResult() {
    return new PublishResult(
        PublishStatus.COMPLETED,
        "post-id",
        "video-id",
        "https://provider.example/post-id",
        "request-id",
        null,
        "completed",
        false);
  }

  @Test
  void rejectsReusingAnIdempotencyKeyForADifferentCommand() {
    PublishCommand first = command("reused-command");
    PublishCommand different = command("reused-command");

    repository.claim(first);

    assertThatThrownBy(() -> repository.claim(different))
        .isInstanceOf(RuntimeException.class)
        .hasMessageContaining("idempotency key");
  }

  @Test
  void duplicateInFlightCommandsDoNotExposeAFictitiousProviderResult() {
    PublishCommand command = command("in-flight-command");

    repository.claim(command);
    ProviderOperationRepository.OperationClaim duplicate = repository.claim(command);

    assertThat(duplicate.newOperation()).isFalse();
    assertThat(duplicate.existingResult()).isEmpty();
  }
}
