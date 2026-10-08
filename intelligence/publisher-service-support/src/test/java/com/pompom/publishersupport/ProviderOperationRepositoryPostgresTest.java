package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublisherCapability;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(
    classes = ProviderOperationRepositoryPostgresTest.TestApplication.class,
    properties = {
      "spring.jpa.hibernate.ddl-auto=validate",
      "spring.flyway.enabled=true",
      "spring.flyway.locations=classpath:db/migration"
    })
@Testcontainers(disabledWithoutDocker = true)
class ProviderOperationRepositoryPostgresTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("publisher_support_test")
          .withUsername("publisher_support")
          .withPassword("publisher_support_test");

  @Autowired private ProviderOperationRepository repository;

  @DynamicPropertySource
  static void databaseProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
  }

  @Test
  void concurrentFirstClaimsReturnOneWinnerAndOneExistingOperation() throws Exception {
    PublishCommand command = command("concurrent-command");
    CountDownLatch ready = new CountDownLatch(2);
    CountDownLatch start = new CountDownLatch(1);
    ExecutorService workers = Executors.newFixedThreadPool(2);
    try {
      Future<ProviderOperationRepository.OperationClaim> first =
          workers.submit(() -> claimAfter(start, ready, command));
      Future<ProviderOperationRepository.OperationClaim> second =
          workers.submit(() -> claimAfter(start, ready, command));
      ready.await();
      start.countDown();

      ProviderOperationRepository.OperationClaim firstClaim = first.get();
      ProviderOperationRepository.OperationClaim secondClaim = second.get();

      assertThat(List.of(firstClaim.newOperation(), secondClaim.newOperation()))
          .containsExactlyInAnyOrder(true, false);
      assertThat(firstClaim.operation().getId()).isEqualTo(secondClaim.operation().getId());
    } finally {
      workers.shutdownNow();
    }
  }

  @Test
  void sameKeyCanBeClaimedIndependentlyPerCapability() {
    PublishCommand command = command("capability-scoped-command");

    ProviderOperationRepository.OperationClaim facebook =
        repository.claim(command, PublisherCapability.FACEBOOK_REELS);
    ProviderOperationRepository.OperationClaim instagram =
        repository.claim(command, PublisherCapability.INSTAGRAM_REELS);

    assertThat(facebook.newOperation()).isTrue();
    assertThat(instagram.newOperation()).isTrue();
    assertThat(facebook.operation().getId()).isNotEqualTo(instagram.operation().getId());
  }

  private ProviderOperationRepository.OperationClaim claimAfter(
      CountDownLatch start, CountDownLatch ready, PublishCommand command) throws Exception {
    ready.countDown();
    start.await();
    return repository.claim(command);
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
}
