package com.pompom.tiktokpublisher.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
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
import com.pompom.tiktokpublisher.client.TikTokContentClient;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class TikTokPublishServiceTest {

  private static final String INTERNAL_TOKEN = "internal-secret";

  @Test
  void completedDuplicateReturnsStoredResultWithoutCallingTikTok() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    ProviderOperationRepository.OperationClaim claim = mockClaim(false, completedResult());
    when(repository.claim(any(PublishCommand.class), eq(PublisherCapability.TIKTOK_VIDEO)))
        .thenReturn(claim);

    TikTokPublishService service =
        service(repository, client, configuredGuard());

    assertThat(service.publish(command(), "tiktok_video")).isEqualTo(completedResult());
    verifyNoInteractions(client);
  }

  @Test
  void inFlightDuplicateReturnsAcceptedWithoutCallingTikTok() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    ProviderOperationRepository.OperationClaim claim = mockClaim(false, (PublishResult) null);
    when(repository.claim(any(PublishCommand.class), eq(PublisherCapability.TIKTOK_VIDEO)))
        .thenReturn(claim);

    PublishResult result =
        service(repository, client, configuredGuard())
            .publish(command(), "tiktok_video");

    assertThat(result.status()).isEqualTo(PublishStatus.ACCEPTED);
    assertThat(result.reconciliationRequired()).isFalse();
    verifyNoInteractions(client);
  }

  @Test
  void newOperationDelegatesToTikTokAndRecordsCapabilityScopedResult() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    ProviderOperationRepository.OperationClaim claim = mockClaim(true, (PublishResult) null);
    PublishResult result = completedResult();
    when(repository.claim(any(PublishCommand.class), eq(PublisherCapability.TIKTOK_VIDEO)))
        .thenReturn(claim);
    when(client.publish(any(PublishCommand.class))).thenReturn(result);

    PublishResult actual =
        service(repository, client, configuredGuard())
            .publish(command(), "tiktok_video");

    assertThat(actual).isEqualTo(result);
    verify(client).publish(any(PublishCommand.class));
    verify(repository)
        .recordResult(
            eq(PublisherCapability.TIKTOK_VIDEO),
            argThat(key -> key.startsWith("tiktok_video:")),
            eq(result));
  }

  @Test
  void reconciliationDelegatesOnlyToStatusLookupAndValidatesIdentity() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    when(repository.findByPublicationAttemptId(
            eq(PublisherCapability.TIKTOK_VIDEO), any(UUID.class)))
        .thenReturn(Optional.empty());
    PublishResult result =
        new PublishResult(
            PublishStatus.COMPLETED,
            "publish-1",
            null,
            "https://tiktok.example/video/1",
            "log-1",
            null,
            null,
            false);
    when(client.reconcile("publish-1")).thenReturn(result);

    TikTokPublishService.ReconcileCommand command =
        new TikTokPublishService.ReconcileCommand(
            UUID.randomUUID(), "tiktok_video", "account-1", "publish-1", null, "log-1");

    PublishResult actual =
        service(repository, client, configuredGuard())
            .reconcile(command);

    assertThat(actual).isEqualTo(result);
    verify(client).reconcile("publish-1");
    verify(client, never()).publish(any(PublishCommand.class));
  }

  @Test
  void refusesCallerIdentityThatDiffersFromStoredProviderIdentityWithoutQueryingOrRecording() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    ProviderOperationRecord record = mock(ProviderOperationRecord.class);
    when(record.getProviderPostId()).thenReturn("stored-publish");
    when(record.getProviderVideoId()).thenReturn(null);
    when(record.getProviderRequestId()).thenReturn("stored-request");
    when(record.getStatus()).thenReturn(PublishStatus.RECONCILIATION_REQUIRED);
    when(repository.findByPublicationAttemptId(
            eq(PublisherCapability.TIKTOK_VIDEO), any(UUID.class)))
        .thenReturn(Optional.of(record));

    TikTokPublishService.ReconcileCommand reconcileCommand =
        new TikTokPublishService.ReconcileCommand(
            UUID.randomUUID(), "tiktok_video", "account-1", "caller-publish", null, null);

    PublishResult result = service(repository, client, configuredGuard()).reconcile(reconcileCommand);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.providerPostId()).isEqualTo("stored-publish");
    verifyNoInteractions(client);
    verify(repository, never())
        .recordResult(eq(PublisherCapability.TIKTOK_VIDEO), any(String.class), any(PublishResult.class));
  }

  @Test
  void refusesMismatchedProviderResultWithoutOverwritingStoredIdentity() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    ProviderOperationRecord record = mock(ProviderOperationRecord.class);
    when(record.getProviderPostId()).thenReturn("stored-publish");
    when(record.getProviderVideoId()).thenReturn(null);
    when(record.getProviderRequestId()).thenReturn("stored-request");
    when(record.getStatus()).thenReturn(PublishStatus.RECONCILIATION_REQUIRED);
    when(repository.findByPublicationAttemptId(
            eq(PublisherCapability.TIKTOK_VIDEO), any(UUID.class)))
        .thenReturn(Optional.of(record));
    when(client.reconcile("stored-publish"))
        .thenReturn(
            new PublishResult(
                PublishStatus.COMPLETED,
                "different-publish",
                null,
                "https://tiktok.example/video/different",
                "new-request",
                null,
                null,
                false));

    TikTokPublishService.ReconcileCommand reconcileCommand =
        new TikTokPublishService.ReconcileCommand(
            UUID.randomUUID(), "tiktok_video", "account-1", "stored-publish", null, null);

    PublishResult result = service(repository, client, configuredGuard()).reconcile(reconcileCommand);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.providerPostId()).isEqualTo("stored-publish");
    verify(repository, never())
        .recordResult(eq(PublisherCapability.TIKTOK_VIDEO), any(String.class), any(PublishResult.class));
  }

  @Test
  void rejectsReuseOfAnIdempotencyKeyForADifferentCommand() {
    ProviderOperationRepository repository = mock(ProviderOperationRepository.class);
    TikTokContentClient client = mock(TikTokContentClient.class);
    when(repository.claim(any(PublishCommand.class), eq(PublisherCapability.TIKTOK_VIDEO)))
        .thenThrow(
            new IllegalArgumentException(
                "idempotency key is already bound to a different publish command"));

    assertThat(
            org.assertj.core.api.Assertions.catchThrowable(
                () ->
                    service(
                            repository,
                            client,
                            configuredGuard())
                        .publish(command(), "tiktok_video")))
        .isInstanceOf(TikTokPublishService.IdempotencyConflictException.class);
  }

  private TikTokPublishService service(
      ProviderOperationRepository repository,
      TikTokContentClient client,
      TikTokWriteCapabilityGuard guard) {
    return new TikTokPublishService(repository, new PublisherRequestValidator(), client, guard);
  }

  private TikTokWriteCapabilityGuard configuredGuard() {
    return new TikTokWriteCapabilityGuard(
        true, true, false, INTERNAL_TOKEN, "access-token", "account-1");
  }

  private ProviderOperationRepository.OperationClaim mockClaim(
      boolean newOperation, PublishResult result) {
    ProviderOperationRepository.OperationClaim claim =
        mock(ProviderOperationRepository.OperationClaim.class);
    when(claim.newOperation()).thenReturn(newOperation);
    when(claim.existingResult()).thenReturn(Optional.ofNullable(result));
    return claim;
  }

  private PublishResult completedResult() {
    return new PublishResult(
        PublishStatus.COMPLETED,
        "publish-1",
        null,
        "https://tiktok.example/video/1",
        "log-1",
        null,
        null,
        false);
  }

  private PublishCommand command() {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "idempotency-1",
        "account-1",
        "/asset/video.mp4",
        "a".repeat(64),
        "title",
        "caption",
        List.of("tag"),
        true,
        Map.of());
  }
}
