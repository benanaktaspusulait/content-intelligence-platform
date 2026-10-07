package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import com.pompom.creative.repository.MetaCommentRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MetaCommentModerationServiceTest {

  @Mock private MetaCommentRepository commentRepository;
  @Mock private MetaCommentReplyRepository replyRepository;
  @Mock private MetaCommentReplyGuard replyGuard;

  @Test
  void createsDraftAndRequiresHumanApprovalBeforeSend() {
    UUID commentId = UUID.randomUUID();
    MetaComment comment =
        MetaComment.builder()
            .id(commentId)
            .thread(
                MetaCommentThread.builder()
                    .platform(PlatformType.INSTAGRAM)
                    .externalObjectId("media-1")
                    .build())
            .externalCommentId("comment-1")
            .text("Nice")
            .build();
    when(commentRepository.findById(commentId)).thenReturn(Optional.of(comment));
    when(replyRepository.findByIdempotencyKey("reply-1")).thenReturn(Optional.empty());
    when(replyRepository.save(any(MetaCommentReply.class)))
        .thenAnswer(
            invocation -> {
              MetaCommentReply reply = invocation.getArgument(0);
              if (reply.getId() == null) reply.setId(UUID.randomUUID());
              return reply;
            });

    MetaCommentModerationService service =
        new MetaCommentModerationService(commentRepository, replyRepository, replyGuard);

    MetaCommentReply reply = service.createDraft(commentId, "Thank you!", "reply-1");
    when(replyRepository.findById(reply.getId())).thenReturn(Optional.of(reply));
    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.DRAFT);

    service.submitForApproval(reply.getId());
    service.approve(reply.getId(), "reviewer");

    assertThat(reply.getStatus()).isEqualTo(MetaCommentReply.Status.APPROVED);
  }
}
