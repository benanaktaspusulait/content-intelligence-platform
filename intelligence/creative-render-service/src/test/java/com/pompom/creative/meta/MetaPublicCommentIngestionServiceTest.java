package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.MetaCommentThreadRepository;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class MetaPublicCommentIngestionServiceTest {

  @Mock private MetaCommentThreadRepository threadRepository;
  @Mock private MetaCommentRepository commentRepository;

  @Test
  void persistsNormalizedCommentIdempotentlyByProviderIdentity() {
    MetaPublicCommentWebhookNormalizer.NormalizedComment event =
        new MetaPublicCommentWebhookNormalizer.NormalizedComment(
            PlatformType.INSTAGRAM,
            "ig-1",
            "media-1",
            "comment-1",
            "Love it",
            null,
            "user-1",
            "viewer",
            null,
            null);
    MetaCommentThread thread =
        MetaCommentThread.builder()
            .id(UUID.randomUUID())
            .externalThreadKey("media-1:comment-1")
            .build();
    when(threadRepository.findByPlatformAndExternalThreadKey(
            PlatformType.INSTAGRAM, "media-1:comment-1"))
        .thenReturn(Optional.of(thread));
    when(commentRepository.findByThreadIdAndExternalCommentId(thread.getId(), "comment-1"))
        .thenReturn(Optional.empty());
    when(commentRepository.save(any(MetaComment.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    MetaPublicCommentIngestionService service =
        new MetaPublicCommentIngestionService(threadRepository, commentRepository);

    MetaComment saved = service.ingest(event);

    assertThat(saved.getExternalCommentId()).isEqualTo("comment-1");
    assertThat(saved.getModerationStatus()).isEqualTo(MetaComment.ModerationStatus.RECEIVED);
    assertThat(saved.getText()).isEqualTo("Love it");
  }
}
