package com.pompom.tiktokpublisher.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.tiktokpublisher.TikTokPublisherApplication;
import com.pompom.tiktokpublisher.client.TikTokContentClient;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(
    classes = TikTokPublisherApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:tiktok_reconciliation;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=validate",
      "spring.flyway.enabled=false",
      "publisher.support.flyway.enabled=true",
      "pompom.tiktok.write-enabled=true",
      "pompom.tiktok.publish-enabled=true",
      "pompom.tiktok.dry-run=false",
      "pompom.tiktok.internal-token=internal-secret",
      "pompom.tiktok.access-token=access-token",
      "pompom.tiktok.api-base-url=https://open.tiktok.test",
      "pompom.tiktok.platform-account-id=account-1"
    })
class TikTokPublishServiceRepositoryTest {

  @Autowired private ProviderOperationRepository repository;
  @Autowired private PublisherRequestValidator requestValidator;
  @Autowired private TikTokWriteCapabilityGuard admission;

  @Test
  void repeatedUnresolvedReconciliationKeepsStoredStateAndNeverPublishes() {
    UUID publicationAttemptId = UUID.randomUUID();
    PublishCommand publishCommand = command(publicationAttemptId);
    String idempotencyKey = publishCommand.idempotencyKey();
    PublishResult initialResult = unresolved("request-0", "initial unresolved observation");
    PublishResult firstObservation = unresolved("request-1", "first unresolved observation");
    PublishResult secondObservation = unresolved("request-2", "second unresolved observation");
    PublishResult terminalObservation =
        new PublishResult(
            PublishStatus.COMPLETED,
            "publish-1",
            null,
            "https://tiktok.example/video/1",
            "request-3",
            null,
            null,
            false);
    ProviderOperationRepository.OperationClaim claim =
        repository.claim(publishCommand, PublisherCapability.TIKTOK_VIDEO);
    assertThat(claim.newOperation()).isTrue();
    repository.recordResult(PublisherCapability.TIKTOK_VIDEO, idempotencyKey, initialResult);

    TikTokContentClient client = mock(TikTokContentClient.class);
    when(client.reconcile("publish-1"))
        .thenReturn(firstObservation, secondObservation, terminalObservation);
    TikTokPublishService service =
        new TikTokPublishService(repository, requestValidator, client, admission);
    TikTokPublishService.ReconcileCommand reconcileCommand =
        new TikTokPublishService.ReconcileCommand(
            publicationAttemptId, "tiktok_video", "account-1", "publish-1", null, "request-0");

    PublishResult first = service.reconcile(reconcileCommand);
    PublishResult second = service.reconcile(reconcileCommand);

    assertThat(first.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(second.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(second.providerRequestId()).isEqualTo("request-2");
    assertThat(second.message()).isEqualTo("second unresolved observation");
    assertThat(second.reconciliationRequired()).isTrue();
    assertThat(repository.findExistingResult(PublisherCapability.TIKTOK_VIDEO, idempotencyKey))
        .contains(initialResult);

    PublishResult terminal = service.reconcile(reconcileCommand);

    assertThat(terminal).isEqualTo(terminalObservation);
    assertThat(repository.findExistingResult(PublisherCapability.TIKTOK_VIDEO, idempotencyKey))
        .contains(terminalObservation);
    verify(client, times(3)).reconcile("publish-1");
    verify(client, never()).publish(any(PublishCommand.class));
  }

  private PublishCommand command(UUID publicationAttemptId) {
    return new PublishCommand(
        UUID.randomUUID(),
        publicationAttemptId,
        "tiktok-reconciliation-" + publicationAttemptId,
        "account-1",
        "/asset/video.mp4",
        "a".repeat(64),
        "title",
        "caption",
        List.of("tag"),
        true,
        Map.of());
  }

  private PublishResult unresolved(String requestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        "publish-1",
        null,
        null,
        requestId,
        PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
        message,
        true);
  }
}
