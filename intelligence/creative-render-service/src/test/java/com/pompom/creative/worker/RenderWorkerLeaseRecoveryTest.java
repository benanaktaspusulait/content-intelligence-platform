package com.pompom.creative.worker;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

/**
 * A worker that dies mid-attempt must not permanently strand that attempt: its lease simply expires
 * and {@link RenderAttemptClaimRepository#claimEligibleAttempts} (proven against real PostgreSQL by
 * {@link RenderAttemptClaimPostgresTest}) makes it eligible again. This test covers {@link
 * RenderWorker}'s side of that contract - it must pass the configured lease duration through on
 * every claim call and tolerate {@link LeaseNotOwnedException} from a dispatched attempt (e.g.
 * because another worker already reclaimed it) without that one attempt derailing the rest of the
 * tick.
 */
@ExtendWith(MockitoExtension.class)
class RenderWorkerLeaseRecoveryTest {

  @Mock private RenderAttemptClaimRepository claimRepository;
  @Mock private RenderAttemptOrchestrator orchestrator;

  @Test
  void tickRequestsALeaseExpiryConsistentWithTheConfiguredLeaseDuration() {
    Duration leaseDuration = Duration.ofSeconds(45);
    RenderWorkerProperties properties =
        new RenderWorkerProperties(true, leaseDuration, 10, Duration.ofSeconds(5));
    RenderWorker worker = new RenderWorker(claimRepository, orchestrator, properties);
    when(claimRepository.claimEligibleAttempts(any(), any(), any(), eq(10))).thenReturn(List.of());

    Instant before = Instant.now();
    worker.tick();
    Instant after = Instant.now();

    ArgumentCaptor<Instant> nowCaptor = ArgumentCaptor.forClass(Instant.class);
    ArgumentCaptor<Instant> leaseExpiresCaptor = ArgumentCaptor.forClass(Instant.class);
    verify(claimRepository)
        .claimEligibleAttempts(any(), nowCaptor.capture(), leaseExpiresCaptor.capture(), eq(10));

    Instant now = nowCaptor.getValue();
    Instant leaseExpiresAt = leaseExpiresCaptor.getValue();
    assertThat(now).isBetween(before, after);
    assertThat(Duration.between(now, leaseExpiresAt)).isEqualTo(leaseDuration);
  }

  @Test
  void aLeaseStolenByAnotherWorkerDuringDispatchDoesNotAbortTheRestOfTheBatch() {
    RenderWorkerProperties properties =
        new RenderWorkerProperties(true, Duration.ofSeconds(30), 10, Duration.ofSeconds(5));
    RenderWorker worker = new RenderWorker(claimRepository, orchestrator, properties);

    UUID reclaimedByAnotherWorker = UUID.randomUUID();
    UUID stillOwned = UUID.randomUUID();
    when(claimRepository.claimEligibleAttempts(any(), any(), any(), eq(10)))
        .thenReturn(List.of(reclaimedByAnotherWorker, stillOwned));
    doThrow(new LeaseNotOwnedException(reclaimedByAnotherWorker, "this-worker", "other-worker"))
        .when(orchestrator)
        .processAttempt(eq(reclaimedByAnotherWorker), any());

    worker.tick();

    verify(orchestrator).processAttempt(eq(reclaimedByAnotherWorker), any());
    verify(orchestrator).processAttempt(eq(stillOwned), any());
  }
}
