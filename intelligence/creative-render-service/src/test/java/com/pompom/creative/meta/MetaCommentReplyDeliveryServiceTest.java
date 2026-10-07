package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
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

@ExtendWith(MockitoExtension.class)
class MetaCommentReplyDeliveryServiceTest {

  @Mock private MetaCommentReplyRepository replyRepository;
  @Mock private MetaCommentDeliveryAttemptRepository attemptRepository;
  @Mock private MetaCommentReplyGuard guard;
  @Mock private MetaCommentReplyPort instagramPort;

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
    lenient().when(replyRepository.findById(reply.getId())).thenReturn(Optional.of(reply));
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
    verify(instagramPort).sendApprovedReply(reply);

    service.send(reply.getId());
    verify(instagramPort).sendApprovedReply(reply);
  }

  @Test
  void ambiguousProviderFailureRequiresReconciliationAndBlocksBlindRetry() {
    when(instagramPort.sendApprovedReply(reply))
        .thenThrow(new RuntimeException(new java.net.SocketTimeoutException("provider timeout")));

    MetaCommentReply result = service.send(reply.getId());
    assertThat(result.getStatus()).isEqualTo(MetaCommentReply.Status.RECONCILIATION_REQUIRED);
    assertThat(reply.getErrorMessage()).contains("provider timeout");

    service.send(reply.getId());
    verify(instagramPort).sendApprovedReply(reply);
  }
}
