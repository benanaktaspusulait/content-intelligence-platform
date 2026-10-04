package com.pompom.creative.queue;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.BudgetAlertService;
import com.pompom.creative.service.CreditTrackingService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Proves the idempotency race-handling path against a real PostgreSQL instance with real concurrent
 * transactions - a behavior that cannot be trusted from mocks alone, since it depends on how the
 * database actually enforces the unique constraint under concurrent inserts.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class RenderJobIdempotencyPostgresTest {

  @Container
  static final PostgreSQLContainer<?> DB =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("creative_render_idempotency_test")
          .withUsername("render")
          .withPassword("render_test");

  @DynamicPropertySource
  static void datasourceProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DB::getJdbcUrl);
    registry.add("spring.datasource.username", DB::getUsername);
    registry.add("spring.datasource.password", DB::getPassword);
  }

  @Autowired RenderJobQueueService queueService;
  @Autowired RenderJobRepository renderJobRepo;
  @MockitoBean IntelligenceValidationEvidenceClient evidenceClient;
  @MockitoBean IntelligenceContentClient contentClient;
  @MockitoBean CreditTrackingService creditTrackingService;
  @MockitoBean BudgetAlertService budgetAlertService;

  @BeforeEach
  void stubEvidence() {
    when(evidenceClient.getEvidence(anyLong())).thenReturn(renderReadyEvidence());
    when(contentClient.fetch(anyLong(), anyLong()))
        .thenReturn(
            new ContentPromptSnapshot(
                "v1", 10L, "Kiko", "REEL", "RENDER_READY", 11L, 1,
                "a".repeat(120), "{}", "a".repeat(64)));
    when(creditTrackingService.canAffordRender(org.mockito.ArgumentMatchers.any())).thenReturn(true);
    when(creditTrackingService.getEstimatedCost(org.mockito.ArgumentMatchers.any()))
        .thenReturn(BigDecimal.TEN);
  }

  @Test
  void concurrentRequestsWithTheSameIdempotencyKeyProduceExactlyOneJob() throws Exception {
    String idempotencyKey = "concurrent-key-" + UUID.randomUUID();
    QueueRenderJobRequest request = request();
    int concurrentRequests = 8;

    ExecutorService pool = Executors.newFixedThreadPool(concurrentRequests);
    try {
      List<Callable<QueueRenderJobResponse>> tasks =
          IntStream.range(0, concurrentRequests)
              .<Callable<QueueRenderJobResponse>>mapToObj(
                  i -> () -> queueService.queue(idempotencyKey, request))
              .toList();

      List<Future<QueueRenderJobResponse>> futures = pool.invokeAll(tasks);

      List<QueueRenderJobResponse> responses = new java.util.ArrayList<>();
      for (Future<QueueRenderJobResponse> future : futures) {
        responses.add(future.get(30, TimeUnit.SECONDS));
      }

      // Every response must point at the same render job id.
      assertThat(responses.stream().map(QueueRenderJobResponse::renderJobId).distinct()).hasSize(1);

      // Exactly one of the concurrent calls actually created the row; the rest observed it as a
      // replay. If the race-handling in RenderJobQueueService failed, more than one row would
      // exist for this key, or every response would incorrectly claim replay=false.
      assertThat(responses.stream().filter(r -> !r.replay())).hasSize(1);

      long rowCountForThisKey =
          renderJobRepo.findByIdempotencyKey(idempotencyKey).map(job -> 1).orElse(0);
      assertThat(rowCountForThisKey).isEqualTo(1);
    } finally {
      pool.shutdownNow();
    }
  }

  @Test
  void secondRequestWithSameKeyDifferentPayloadIsRejectedAfterFirstSucceeds() {
    String idempotencyKey = "sequential-conflict-" + UUID.randomUUID();
    QueueRenderJobResponse first = queueService.queue(idempotencyKey, request());
    assertThat(first.replay()).isFalse();

    QueueRenderJobRequest differentPayload =
        new QueueRenderJobRequest(
            request().contentId(),
            request().promptVersionId(),
            request().validationRecordId(),
            request().jobType(),
            "a-completely-different-model",
            Map.of(),
            null);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () -> queueService.queue(idempotencyKey, differentPayload))
        .isInstanceOf(IdempotencyKeyConflictException.class);

    // The conflicting attempt must not have created a second row for this key.
    assertThat(renderJobRepo.findByIdempotencyKey(idempotencyKey)).isPresent();
    long matchingRows =
        renderJobRepo.findAll().stream()
            .filter(job -> job.getIdempotencyKey().equals(idempotencyKey))
            .count();
    assertThat(matchingRows).isEqualTo(1);
  }

  private QueueRenderJobRequest request() {
    return new QueueRenderJobRequest(
        10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
  }

  private ValidationEvidenceDto renderReadyEvidence() {
    Instant now = Instant.now();
    return new ValidationEvidenceDto(
        42L,
        10L,
        11L,
        "a".repeat(64),
        "RENDER_READY",
        0,
        0,
        0,
        "1.0",
        "openai",
        "gpt-4o",
        "1.0",
        UUID.randomUUID(),
        now.minusSeconds(60),
        now.minusSeconds(60),
        now.plusSeconds(3600));
  }
}
