package com.pompom.youtubepublisher.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRecord;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.youtubepublisher.client.YouTubeDataClient;
import com.pompom.youtubepublisher.security.YouTubeWriteCapabilityGuard;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;

class YouTubePublishServiceTest {

  private static final String CAPABILITY = "youtube_shorts";
  private static final Instant NOW = Instant.parse("2026-10-08T12:00:00Z");

  private final ProviderOperationRepository operationRepository =
      mock(ProviderOperationRepository.class);
  private final PublisherRequestValidator requestValidator = mock(PublisherRequestValidator.class);
  private final YouTubeDataClient client = mock(YouTubeDataClient.class);
  private final YouTubeWriteCapabilityGuard admission = mock(YouTubeWriteCapabilityGuard.class);
  private final ProviderOperationRepository.OperationClaim claim =
      mock(ProviderOperationRepository.OperationClaim.class);
  private final YouTubePublishService service =
      new YouTubePublishService(
          operationRepository,
          requestValidator,
          client,
          admission,
          Clock.fixed(NOW, ZoneOffset.UTC),
          Duration.ofMinutes(5));

  @BeforeEach
  void configureAdmission() {
    when(admission.normalizeCapability(CAPABILITY)).thenReturn(CAPABILITY);
  }

  @Test
  void firstClaimPublishesAndRecordsTheClientResult() {
    PublishCommand command = command("first-command");
    PublishResult completed = completedResult();
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(client.publish(any(PublishCommand.class))).thenReturn(completed);

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result).isEqualTo(completed);
    InOrder order = inOrder(operationRepository, client);
    order
        .verify(operationRepository)
        .claim(any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY)));
    order.verify(client).publish(any(PublishCommand.class));
    order
        .verify(operationRepository)
        .recordResult(eq(PublisherCapability.of(CAPABILITY)), any(String.class), eq(completed));
  }

  @Test
  void completedDuplicateReturnsPersistedResultWithoutProviderCall() {
    PublishCommand command = command("completed-duplicate");
    PublishResult completed = completedResult();
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(false);
    when(claim.existingResult()).thenReturn(Optional.of(completed));

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result).isEqualTo(completed);
    verifyNoInteractions(client);
    verify(operationRepository, never())
        .recordResult(any(PublisherCapability.class), any(String.class), any(PublishResult.class));
  }

  @Test
  void freshInFlightDuplicateRemainsAccepted() {
    PublishCommand command = command("fresh-in-flight");
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(false);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(claim.isStale(NOW, Duration.ofMinutes(5))).thenReturn(false);

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result.status()).isEqualTo(PublishStatus.ACCEPTED);
    assertThat(result.reconciliationRequired()).isFalse();
    verifyNoInteractions(client);
    verify(operationRepository, never())
        .recordResult(any(PublisherCapability.class), any(String.class), any(PublishResult.class));
  }

  @Test
  void staleInFlightDuplicateIsPersistedAsReconciliationRequired() {
    PublishCommand command = command("stale-in-flight");
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(false);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(claim.isStale(NOW, Duration.ofMinutes(5))).thenReturn(true);

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    verifyNoInteractions(client);
    verify(operationRepository)
        .recordResult(eq(PublisherCapability.of(CAPABILITY)), any(String.class), eq(result));
  }

  @Test
  void admissionFailureOccursBeforeClaim() {
    PublishCommand command = command("admission-failure");
    doThrow(new YouTubeWriteCapabilityGuard.ForbiddenException())
        .when(admission)
        .assertProviderConfigured(CAPABILITY, command.platformAccountId(), true);

    assertThatThrownBy(() -> service.publish(command, CAPABILITY))
        .isInstanceOf(YouTubeWriteCapabilityGuard.ForbiddenException.class);

    verifyNoInteractions(operationRepository, client);
  }

  @Test
  void clientExceptionIsRecordedAsReconciliationRequired() {
    PublishCommand command = command("client-failure");
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(client.publish(any(PublishCommand.class)))
        .thenThrow(new IllegalStateException("transport"));

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    verify(operationRepository)
        .recordResult(eq(PublisherCapability.of(CAPABILITY)), any(String.class), eq(result));
  }

  @Test
  void nullClientResultIsRecordedAsReconciliationRequired() {
    PublishCommand command = command("null-client-result");
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenReturn(claim);
    when(claim.newOperation()).thenReturn(true);
    when(claim.existingResult()).thenReturn(Optional.empty());
    when(client.publish(any(PublishCommand.class))).thenReturn(null);

    PublishResult result = service.publish(command, CAPABILITY);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    verify(operationRepository)
        .recordResult(eq(PublisherCapability.of(CAPABILITY)), any(String.class), eq(result));
  }

  @Test
  void reconciliationUsesReadOnlyClientAndAdvancesTheBoundOperation() {
    UUID attemptId = UUID.randomUUID();
    YouTubePublishService.ReconcileCommand command =
        new YouTubePublishService.ReconcileCommand(
            attemptId, CAPABILITY, "youtube-account-1", "video-123", "request-1");
    ProviderOperationRecord record = mock(ProviderOperationRecord.class);
    PublishResult completed = completedResult();
    when(operationRepository.findByPublicationAttemptId(
            PublisherCapability.of(CAPABILITY), attemptId))
        .thenReturn(Optional.of(record));
    when(record.getProviderVideoId()).thenReturn(null);
    when(record.getStatus()).thenReturn(null);
    when(record.getCommandIdempotencyKey()).thenReturn("bound-command");
    when(client.reconcile("video-123")).thenReturn(completed);

    PublishResult result = service.reconcile(command);

    assertThat(result).isEqualTo(completed);
    verify(client).reconcile("video-123");
    verify(operationRepository)
        .recordResult(PublisherCapability.of(CAPABILITY), "bound-command", completed);
  }

  @Test
  void reconciliationIdentityMismatchDoesNotOverwriteStoredIdentity() {
    UUID attemptId = UUID.randomUUID();
    YouTubePublishService.ReconcileCommand command =
        new YouTubePublishService.ReconcileCommand(
            attemptId, CAPABILITY, "youtube-account-1", "requested-video", null);
    ProviderOperationRecord record = mock(ProviderOperationRecord.class);
    when(operationRepository.findByPublicationAttemptId(
            PublisherCapability.of(CAPABILITY), attemptId))
        .thenReturn(Optional.of(record));
    when(record.getProviderVideoId()).thenReturn("stored-video");
    when(record.getProviderRequestId()).thenReturn("stored-request");

    PublishResult result = service.reconcile(command);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.providerVideoId()).isEqualTo("stored-video");
    verifyNoInteractions(client);
    verify(operationRepository, never())
        .recordResult(any(PublisherCapability.class), any(String.class), any(PublishResult.class));
  }

  @Test
  void idempotencyConflictIsExposedAsTheServiceConflict() {
    PublishCommand command = command("conflicting-command");
    when(operationRepository.claim(
            any(PublishCommand.class), eq(PublisherCapability.of(CAPABILITY))))
        .thenThrow(
            new IllegalArgumentException(
                "idempotency key is already bound to a different publish command"));

    assertThatThrownBy(() -> service.publish(command, CAPABILITY))
        .isInstanceOf(YouTubePublishService.IdempotencyConflictException.class);
    verifyNoInteractions(client);
  }

  private PublishCommand command(String key) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        key,
        "youtube-account-1",
        "immutable-asset-reference",
        "a".repeat(64),
        "Title",
        "caption",
        List.of("shorts"),
        true,
        Map.of());
  }

  private PublishResult completedResult() {
    return new PublishResult(
        PublishStatus.COMPLETED,
        null,
        "video-123",
        "https://youtube.com/shorts/video-123",
        "request-1",
        null,
        null,
        false);
  }
}
