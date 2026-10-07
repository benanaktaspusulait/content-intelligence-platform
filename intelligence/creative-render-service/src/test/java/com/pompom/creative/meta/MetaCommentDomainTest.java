package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.PlatformType;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class MetaCommentDomainTest {

  @Test
  void replyRequiresApprovalBeforeItCanBeSent() {
    MetaCommentThread thread =
        MetaCommentThread.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.INSTAGRAM)
            .externalObjectId("media-1")
            .externalThreadKey("media-1:comment-1")
            .build();
    MetaComment comment =
        MetaComment.builder()
            .id(UUID.randomUUID())
            .thread(thread)
            .externalCommentId("comment-1")
            .text("Love this")
            .build();
    MetaCommentReply reply =
        MetaCommentReply.builder()
            .id(UUID.randomUUID())
            .comment(comment)
            .draftText("Thank you!")
            .idempotencyKey("reply-1")
            .build();

    reply.submitForApproval();
    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.PENDING_APPROVAL);

    reply.approve("reviewer");
    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.APPROVED);
    assertThat(reply.getApprovedBy()).isEqualTo("reviewer");

    reply.markSent("provider-reply-1");
    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.SENT);
    assertThat(reply.getProviderReplyId()).isEqualTo("provider-reply-1");
    assertThat(reply.getSentAt()).isNotNull();
  }

  @Test
  void failedReplyCanBeMarkedRetryableWithoutLosingAuditText() {
    MetaCommentReply reply =
        MetaCommentReply.builder()
            .draftText("Thanks for watching!")
            .status(MetaCommentReply.Status.APPROVED)
            .build();

    reply.markFailed("rate limited", true);

    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.RETRYABLE);
    assertThat(reply.getErrorMessage()).isEqualTo("rate limited");
    assertThat(reply.getDraftText()).isEqualTo("Thanks for watching!");
  }
}
