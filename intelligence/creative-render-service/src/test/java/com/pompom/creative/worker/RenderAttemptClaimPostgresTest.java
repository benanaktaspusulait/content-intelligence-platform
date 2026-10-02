package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Proves {@link RenderAttemptClaimRepository}'s concurrency and lease semantics against a real
 * PostgreSQL instance - behavior that cannot be trusted from mocks, since it depends on how {@code
 * FOR UPDATE SKIP LOCKED} actually arbitrates between real concurrent transactions.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class RenderAttemptClaimPostgresTest {

  @Container
  static final PostgreSQLContainer<?> DB =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("creative_render_claim_test")
          .withUsername("render")
          .withPassword("render_test");

  @DynamicPropertySource
  static void datasourceProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DB::getJdbcUrl);
    registry.add("spring.datasource.username", DB::getUsername);
    registry.add("spring.datasource.password", DB::getPassword);
  }

  @Autowired RenderJobRepository renderJobRepo;
  @Autowired RenderAttemptRepository renderAttemptRepo;
  @Autowired RenderAttemptClaimRepository claimRepo;

  private RenderJob job;

  @BeforeEach
  void seedJob() {
    // Each test shares the one Testcontainers Postgres instance; clear state left by prior
    // tests in this class so claim-eligibility assertions aren't polluted by earlier rows.
    renderAttemptRepo.deleteAll();
    renderJobRepo.deleteAll();

    job =
        renderJobRepo.save(
            RenderJob.builder()
                .contentId(10L)
                .promptVersionId(11L)
                .contentTitleSnapshot("title")
                .promptVersionNumberSnapshot(1)
                .promptSha256("a".repeat(64))
                .promptTextSnapshot("a".repeat(120))
                .jobType(RenderJob.JobType.VIDEO)
                .openartModel("model-x")
                .build());
  }

  @Test
  void twoWorkersCannotClaimTheSameAttempt() throws Exception {
    RenderAttempt attempt = saveAttempt(RenderExecutionStage.QUEUED, null, null);
    int workers = 2;

    ExecutorService pool = Executors.newFixedThreadPool(workers);
    try {
      List<Callable<List<UUID>>> tasks =
          IntStream.range(0, workers)
              .<Callable<List<UUID>>>mapToObj(
                  i ->
                      () ->
                          claimRepo.claimEligibleAttempts(
                              "worker-" + i, Instant.now(), Instant.now().plusSeconds(60), 10))
              .toList();

      List<Future<List<UUID>>> futures = pool.invokeAll(tasks);
      List<UUID> allClaimed =
          futures.stream()
              .flatMap(
                  f -> {
                    try {
                      return f.get(10, TimeUnit.SECONDS).stream();
                    } catch (Exception e) {
                      throw new RuntimeException(e);
                    }
                  })
              .collect(Collectors.toList());

      // Exactly one worker claimed the single eligible attempt; the other got nothing.
      assertThat(allClaimed).containsExactly(attempt.getId());
    } finally {
      pool.shutdownNow();
    }
  }

  @Test
  void activeLeaseIsNotStolen() {
    saveAttempt(
        RenderExecutionStage.QUEUED,
        "worker-a",
        Instant.now().plusSeconds(300)); // active, far-future lease

    List<UUID> claimed =
        claimRepo.claimEligibleAttempts(
            "worker-b", Instant.now(), Instant.now().plusSeconds(60), 10);

    assertThat(claimed).isEmpty();
  }

  @Test
  void expiredLeaseIsReclaimed() {
    RenderAttempt attempt =
        saveAttempt(
            RenderExecutionStage.POLLING,
            "worker-a",
            Instant.now().minusSeconds(10)); // lease already expired

    List<UUID> claimed =
        claimRepo.claimEligibleAttempts(
            "worker-b", Instant.now(), Instant.now().plusSeconds(60), 10);

    assertThat(claimed).containsExactly(attempt.getId());
  }

  @Test
  void nextPollAtInTheFutureIsNotClaimed() {
    saveAttemptWithNextPoll(Instant.now().plusSeconds(300));

    List<UUID> claimed =
        claimRepo.claimEligibleAttempts(
            "worker-a", Instant.now(), Instant.now().plusSeconds(60), 10);

    assertThat(claimed).isEmpty();
  }

  @Test
  void duePollTimeIsClaimed() {
    RenderAttempt attempt = saveAttemptWithNextPoll(Instant.now().minusSeconds(1));

    List<UUID> claimed =
        claimRepo.claimEligibleAttempts(
            "worker-a", Instant.now(), Instant.now().plusSeconds(60), 10);

    assertThat(claimed).containsExactly(attempt.getId());
  }

  @Test
  void terminalAttemptsAreNeverClaimed() {
    saveAttempt(RenderExecutionStage.COMPLETE, null, null);
    saveAttempt(RenderExecutionStage.FAILED, null, null);
    saveAttempt(RenderExecutionStage.ABANDONED, null, null);
    saveAttempt(RenderExecutionStage.NEEDS_HUMAN_REVIEW, null, null);
    // RETRY_WAIT is a dead end for this specific row too: the rerender that produced it always
    // inserts a new attempt to carry the job forward, and processAttempt has no stage handler
    // for RETRY_WAIT - if this were claimable, a worker would eventually crash on it.
    saveAttempt(RenderExecutionStage.RETRY_WAIT, null, null);

    List<UUID> claimed =
        claimRepo.claimEligibleAttempts(
            "worker-a", Instant.now(), Instant.now().plusSeconds(60), 10);

    assertThat(claimed).isEmpty();
  }

  @Test
  void claimingSetsLeaseOwnerAndExpiry() {
    RenderAttempt attempt = saveAttempt(RenderExecutionStage.QUEUED, null, null);
    Instant now = Instant.now();
    Instant leaseExpiry = now.plusSeconds(120);

    List<UUID> claimed = claimRepo.claimEligibleAttempts("worker-a", now, leaseExpiry, 10);

    assertThat(claimed).containsExactly(attempt.getId());
    RenderAttempt reloaded = renderAttemptRepo.findById(attempt.getId()).orElseThrow();
    assertThat(reloaded.getLeaseOwner()).isEqualTo("worker-a");
    assertThat(reloaded.getLeaseExpiresAt())
        .isCloseTo(
            leaseExpiry,
            org.assertj.core.api.Assertions.within(1, java.time.temporal.ChronoUnit.SECONDS));
  }

  @Test
  void uniqueAttemptNumberPerJobIsEnforcedByTheDatabase() {
    saveAttempt(RenderExecutionStage.QUEUED, null, null);

    org.assertj.core.api.Assertions.assertThatThrownBy(
            () ->
                renderAttemptRepo.saveAndFlush(
                    RenderAttempt.builder()
                        .renderJobId(job.getId())
                        .attemptNumber(1) // duplicate attempt_number for the same job
                        .stage(RenderExecutionStage.QUEUED)
                        .build()))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);

    assertThat(renderAttemptRepo.findByRenderJobIdOrderByAttemptNumberAsc(job.getId())).hasSize(1);
  }

  private RenderAttempt saveAttempt(
      RenderExecutionStage stage, String leaseOwner, Instant leaseExpiresAt) {
    int nextAttemptNumber =
        renderAttemptRepo.findByRenderJobIdOrderByAttemptNumberAsc(job.getId()).size() + 1;
    return renderAttemptRepo.save(
        RenderAttempt.builder()
            .renderJobId(job.getId())
            .attemptNumber(nextAttemptNumber)
            .stage(stage)
            .leaseOwner(leaseOwner)
            .leaseExpiresAt(leaseExpiresAt)
            .build());
  }

  private RenderAttempt saveAttemptWithNextPoll(Instant nextPollAt) {
    int nextAttemptNumber =
        renderAttemptRepo.findByRenderJobIdOrderByAttemptNumberAsc(job.getId()).size() + 1;
    return renderAttemptRepo.save(
        RenderAttempt.builder()
            .renderJobId(job.getId())
            .attemptNumber(nextAttemptNumber)
            .stage(RenderExecutionStage.POLLING)
            .nextPollAt(nextPollAt)
            .build());
  }
}
