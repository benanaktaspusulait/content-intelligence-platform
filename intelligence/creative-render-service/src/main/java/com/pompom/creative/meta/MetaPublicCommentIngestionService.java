package com.pompom.creative.meta;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.MetaCommentThreadRepository;
import java.time.Instant;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Idempotently persists normalized public comment webhook events. */
@Service
@RequiredArgsConstructor
public class MetaPublicCommentIngestionService {

  private final MetaCommentThreadRepository threadRepository;
  private final MetaCommentRepository commentRepository;

  @Transactional
  public MetaComment ingest(MetaPublicCommentWebhookNormalizer.NormalizedComment event) {
    String rootId = event.parentCommentId() == null ? event.commentId() : event.parentCommentId();
    String threadKey = event.objectId() + ":" + rootId;
    MetaCommentThread thread =
        threadRepository
            .findByPlatformAndExternalThreadKey(event.platform(), threadKey)
            .orElseGet(
                () ->
                    threadRepository.save(
                        MetaCommentThread.builder()
                            .platform(event.platform())
                            .externalAccountId(event.accountId())
                            .externalObjectId(event.objectId())
                            .externalThreadKey(threadKey)
                            .lastProviderEventAt(event.providerCreatedAt())
                            .build()));
    thread.setLastProviderEventAt(
        event.providerCreatedAt() == null ? Instant.now() : event.providerCreatedAt());
    threadRepository.save(thread);

    MetaComment comment =
        commentRepository
            .findByThreadIdAndExternalCommentId(thread.getId(), event.commentId())
            .orElseGet(
                () ->
                    MetaComment.builder()
                        .thread(thread)
                        .externalCommentId(event.commentId())
                        .direction(MetaComment.Direction.INBOUND)
                        .moderationStatus(MetaComment.ModerationStatus.RECEIVED)
                        .build());
    comment.setExternalParentCommentId(event.parentCommentId());
    comment.setExternalAuthorId(event.authorId());
    comment.setAuthorDisplayName(event.authorDisplayName());
    comment.setText(event.text());
    comment.setProviderPermalink(event.permalink());
    comment.setProviderCreatedAt(event.providerCreatedAt());
    return commentRepository.save(comment);
  }
}
