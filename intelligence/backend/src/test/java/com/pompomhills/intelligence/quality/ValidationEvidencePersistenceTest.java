package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Verifies the V30 migration's constraints against a real PostgreSQL instance: non-negative counts,
 * the prompt SHA-256 format check, and the partial unique index on independent revalidation ID.
 * {@link ValidationEvidenceServiceTest} covers the service-level completeness logic against mocks;
 * this test covers what only the database itself enforces.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class ValidationEvidencePersistenceTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired QualityValidationRepository repository;

  @Test
  void persistsAndReadsBackACompleteEvidenceRecord() {
    QualityValidationEntity entity = baseEntity();
    entity.setContentId(10L);
    entity.setPromptVersionId(11L);
    entity.setPromptSha256("a".repeat(64));
    entity.setIndependentRevalidationId(UUID.randomUUID());

    QualityValidationEntity saved = repository.save(entity);

    QualityValidationEntity reloaded = repository.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getContentId()).isEqualTo(10L);
    assertThat(reloaded.getPromptSha256()).hasSize(64);
  }

  @Test
  void persistsAndReadsBackAPrecisionSensitiveOverallScore() {
    QualityValidationEntity entity = baseEntity();
    entity.setOverallScore(82.567);

    QualityValidationEntity saved = repository.saveAndFlush(entity);

    QualityValidationEntity reloaded = repository.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getOverallScore()).isEqualTo(82.567);
  }

  @Test
  void persistsAndReadsBackARecordWithNullOverallScore() {
    QualityValidationEntity entity = baseEntity();
    entity.setOverallScore(null);

    QualityValidationEntity saved = repository.saveAndFlush(entity);

    QualityValidationEntity reloaded = repository.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getOverallScore()).isNull();
  }

  @Test
  void rejectsNegativeBlockerCountAtTheDatabase() {
    QualityValidationEntity entity = baseEntity();
    entity.setBlockerCount(-1);

    assertThatThrownBy(() -> repository.saveAndFlush(entity))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  @Test
  void rejectsMalformedPromptHashAtTheDatabase() {
    QualityValidationEntity entity = baseEntity();
    entity.setPromptSha256("not-sha256");

    assertThatThrownBy(() -> repository.saveAndFlush(entity))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  @Test
  void rejectsDuplicateIndependentRevalidationId() {
    UUID sharedRevalidationId = UUID.randomUUID();

    QualityValidationEntity first = baseEntity();
    first.setIndependentRevalidationId(sharedRevalidationId);
    repository.saveAndFlush(first);

    QualityValidationEntity second = baseEntity();
    second.setIndependentRevalidationId(sharedRevalidationId);

    assertThatThrownBy(() -> repository.saveAndFlush(second))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  @Test
  void allowsManyRecordsWithNullIndependentRevalidationId() {
    // The partial unique index must only constrain non-null values - legacy and
    // not-yet-independently-revalidated rows must coexist freely.
    QualityValidationEntity first = baseEntity();
    QualityValidationEntity second = baseEntity();

    repository.saveAndFlush(first);
    repository.saveAndFlush(second);

    assertThat(first.getIndependentRevalidationId()).isNull();
    assertThat(second.getIndependentRevalidationId()).isNull();
  }

  private QualityValidationEntity baseEntity() {
    QualityValidationEntity entity = new QualityValidationEntity();
    entity.setPromptText("a".repeat(120));
    entity.setRulesetVersion("1.0");
    entity.setOverallScore(90.0);
    entity.setStatus("NEEDS_REVISION");
    entity.setBlockerCount(0);
    entity.setCriticalCount(0);
    entity.setWarningCount(0);
    entity.setValidatedAt(Instant.now());
    return entity;
  }
}
