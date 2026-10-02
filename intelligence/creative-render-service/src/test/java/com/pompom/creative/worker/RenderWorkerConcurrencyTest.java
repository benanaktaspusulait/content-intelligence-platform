package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import java.time.Duration;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * {@link RenderWorker#tick} must claim a batch of eligible attempts under one lease owner and
 * dispatch each to {@link RenderAttemptOrchestrator#processAttempt} - this is what makes it safe to
 * run several worker processes/instances concurrently: each tick's claim is atomic (see {@link
 * RenderAttemptClaimPostgresTest}), so two workers calling {@code tick()} at the same moment never
 * receive overlapping attempt IDs, and this test only needs to verify the single-worker dispatch
 * contract against that already-proven claim boundary.
 */
@ExtendWith(MockitoExtension.class)
class RenderWorkerConcurrencyTest {

  @Mock private RenderAttemptClaimRepository claimRepository;
  @Mock private RenderAttemptOrchestrator orchestrator;

  private RenderWorker worker;

  @BeforeEach
  void setUp() {
    RenderWorkerProperties properties =
        new RenderWorkerProperties(true, Duration.ofSeconds(30), 10, Duration.ofSeconds(5));
    worker = new RenderWorker(claimRepository, orchestrator, properties);
  }

  @Test
  void tickClaimsBatchAndProcessesEachClaimedAttemptUnderTheSameLeaseOwner() {
    UUID attempt1 = UUID.randomUUID();
    UUID attempt2 = UUID.randomUUID();
    when(claimRepository.claimEligibleAttempts(anyString(), any(), any(), eq(10)))
        .thenReturn(List.of(attempt1, attempt2));

    worker.tick();

    ArgumentCaptor<String> leaseOwnerCaptor = ArgumentCaptor.forClass(String.class);
    verify(orchestrator).processAttempt(eq(attempt1), leaseOwnerCaptor.capture());
    verify(orchestrator).processAttempt(eq(attempt2), leaseOwnerCaptor.capture());

    // Both dispatches in the same tick must use the exact lease owner the claim call used.
    ArgumentCaptor<String> claimOwnerCaptor = ArgumentCaptor.forClass(String.class);
    verify(claimRepository).claimEligibleAttempts(claimOwnerCaptor.capture(), any(), any(), eq(10));
    assertThat(leaseOwnerCaptor.getAllValues())
        .allMatch(owner -> owner.equals(claimOwnerCaptor.getValue()));
  }

  @Test
  void tickDoesNothingWhenNoAttemptsAreEligible() {
    when(claimRepository.claimEligibleAttempts(anyString(), any(), any(), anyInt()))
        .thenReturn(List.of());

    worker.tick();

    verifyNoInteractions(orchestrator);
  }

  @Test
  void tickSkipsClaimingEntirelyWhenWorkerDisabled() {
    RenderWorkerProperties disabled =
        new RenderWorkerProperties(false, Duration.ofSeconds(30), 10, Duration.ofSeconds(5));
    worker = new RenderWorker(claimRepository, orchestrator, disabled);

    worker.tick();

    verifyNoInteractions(claimRepository, orchestrator);
  }

  @Test
  void oneFailingAttemptDoesNotPreventOthersInTheSameBatchFromProcessing() {
    UUID failing = UUID.randomUUID();
    UUID succeeding = UUID.randomUUID();
    when(claimRepository.claimEligibleAttempts(anyString(), any(), any(), eq(10)))
        .thenReturn(List.of(failing, succeeding));
    doThrow(new RuntimeException("boom"))
        .when(orchestrator)
        .processAttempt(eq(failing), anyString());

    worker.tick();

    verify(orchestrator).processAttempt(eq(failing), anyString());
    verify(orchestrator).processAttempt(eq(succeeding), anyString());
  }
}
