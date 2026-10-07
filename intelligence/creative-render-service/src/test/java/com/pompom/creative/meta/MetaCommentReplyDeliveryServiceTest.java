package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentDeliveryAttempt;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.MetaCommentDeliveryAttemptRepository;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.support.TransactionTemplate;

@ExtendWith(MockitoExtension.class)
class MetaCommentReplyDeliveryServiceTest {

  @Mock private MetaCommentReplyRepository replyRepository;
  @Mock private MetaCommentDeliveryAttemptRepository attemptRepository;
  @Mock private MetaCommentReplyGuard guard;
  @Mock private MetaCommentReplyPort instagramPort;
  @Mock private TransactionTemplate transactionTemplate;

  private MetaCommentReplyDeliveryService service;
  private MetaCommentReply reply;

  @BeforeEach
  void setUp() {
    service =
        new MetaCommentReplyDeliveryService(
            replyRepository,
            attemptRepository,
            Map.of(PlatformType.INSTAGRAM, instagramPort),
            guard);
    reply =
        MetaCommentReply.builder()
            .id(UUID.randomUUID())
            .comment(
                MetaComment.builder()
                    .thread(MetaCommentThread.builder().platform(PlatformType.INSTAGRAM).build())
                    .build())
            .draftText("Thank you!")
            .idempotencyKey("reply-key")
            .status(MetaCommentReply.Status.APPROVED)
            .build();
    lenient().when(replyRepository.findByIdForUpdate(reply.getId())).thenReturn(Optional.of(reply));
    lenient()
        .when(attemptRepository.findTopByReplyIdOrderByAttemptNumberDesc(reply.getId()))
        .thenReturn(Optional.empty());
    lenient()
        .when(attemptRepository.save(any(MetaCommentDeliveryAttempt.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    lenient()
        .when(replyRepository.save(any(MetaCommentReply.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
  }

  @Test
  void refusesUnapprovedReplyBeforeProviderCall() {
    reply.setStatus(MetaCommentReply.Status.PENDING_APPROVAL);

    assertThatThrownBy(() -> service.send(reply.getId()))
        .isInstanceOf(IllegalStateException.class)
        .hasMessageContaining("approval");

    verify(instagramPort, never()).sendApprovedReply(any());
  }

  @Test
  void refusesReplyWhenTheDedicatedKillSwitchIsOff() {
    org.mockito.Mockito.doThrow(new com.pompom.creative.oauth.MetaCommentReplyDisabledException())
        .when(guard)
        .assertAllowed(PlatformType.INSTAGRAM);

    assertThatThrownBy(() -> service.send(reply.getId()))
        .isInstanceOf(com.pompom.creative.oauth.MetaCommentReplyDisabledException.class);

    verify(instagramPort, never()).sendApprovedReply(any());
  }

  @Test
  void persistsProviderIdentityAndDoesNotSendAgainAfterSuccess() {
    when(instagramPort.sendApprovedReply(reply))
        .thenReturn(MetaCommentReplyPort.SendResult.success("provider-reply-1"));

    MetaCommentReply sent = service.send(reply.getId());
    assertThat(sent.getStatus()).isEqualTo(MetaCommentReply.Status.SENT);
    assertThat(sent.getProviderReplyId()).isEqualTo("provider-reply-1");

    service.send(reply.getId());
    verify(instagramPort, times(1)).sendApprovedReply(reply);
  }

  @Test
  void ambiguousProviderFailureRequiresReconciliationAndBlocksBlindRetry() {
    when(instagramPort.sendApprovedReply(reply))
        .thenThrow(new RuntimeException(new java.net.SocketTimeoutException("provider timeout")));

    MetaCommentReply result = service.send(reply.getId());
    assertThat(result.getStatus()).isEqualTo(MetaCommentReply.Status.RECONCILIATION_REQUIRED);
    assertThat(reply.getErrorMessage()).contains("provider timeout");

    service.send(reply.getId());
    verify(instagramPort, times(1)).sendApprovedReply(reply);
  }

  @Test
  void staleSubmittingAttemptIsClosedForReconciliationWithoutProviderRetry() {
    MetaCommentDeliveryAttempt previous =
        MetaCommentDeliveryAttempt.builder()
            .reply(reply)
            .attemptNumber(1)
            .status(MetaCommentDeliveryAttempt.Status.SUBMITTING)
            .build();
    when(attemptRepository.findTopByReplyIdOrderByAttemptNumberDesc(reply.getId()))
        .thenReturn(Optional.of(previous));

    MetaCommentReply result = service.send(reply.getId());

    assertThat(result.getStatus()).isEqualTo(MetaCommentReply.Status.RECONCILIATION_REQUIRED);
    assertThat(previous.getStatus())
        .isEqualTo(MetaCommentDeliveryAttempt.Status.RECONCILIATION_REQUIRED);
    assertThat(previous.getCompletedAt()).isNotNull();
    verify(attemptRepository).save(previous);
    verify(instagramPort, never()).sendApprovedReply(any());
  }

  @Test
  void providerTransportAndServerErrorsRequireReconciliation() {
    when(instagramPort.sendApprovedReply(reply))
        .thenThrow(new org.springframework.web.client.ResourceAccessException("connection reset"));

    MetaCommentReply result = service.send(reply.getId());

    assertThat(result.getStatus()).isEqualTo(MetaCommentReply.Status.RECONCILIATION_REQUIRED);
    verify(instagramPort, times(1)).sendApprovedReply(reply);
  }

  @Test
  void providerServerResponseRequiresReconciliation() {
    when(instagramPort.sendApprovedReply(reply))
        .thenThrow(
            new org.springframework.web.client.HttpServerErrorException(
                org.springframework.http.HttpStatus.BAD_GATEWAY, "provider unavailable"));

    MetaCommentReply result = service.send(reply.getId());

    assertThat(result.getStatus()).isEqualTo(MetaCommentReply.Status.RECONCILIATION_REQUIRED);
    verify(instagramPort, times(1)).sendApprovedReply(reply);
  }

  @Test
  void commitsClaimBeforeProviderCallAndFinalizesSeparately() {
    when(transactionTemplate.execute(any()))
        .thenAnswer(
            invocation -> {
              org.springframework.transaction.support.TransactionCallback<?> callback =
                  invocation.getArgument(0);
              return callback.doInTransaction(null);
            });
    org.mockito.Mockito.doAnswer(
            invocation -> {
              java.util.function.Consumer<org.springframework.transaction.TransactionStatus>
                  callback = invocation.getArgument(0);
              callback.accept(null);
              return null;
            })
        .when(transactionTemplate)
        .executeWithoutResult(any());
    service =
        new MetaCommentReplyDeliveryService(
            replyRepository,
            attemptRepository,
            Map.of(PlatformType.INSTAGRAM, instagramPort),
            guard,
            transactionTemplate);
    when(instagramPort.sendApprovedReply(reply))
        .thenReturn(MetaCommentReplyPort.SendResult.success("provider-reply-1"));

    org.mockito.InOrder order = inOrder(transactionTemplate, instagramPort);
    service.send(reply.getId());

    order.verify(transactionTemplate).execute(any());
    order.verify(instagramPort).sendApprovedReply(reply);
    order.verify(transactionTemplate).executeWithoutResult(any());
  }
}
