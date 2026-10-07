package com.pompom.creative.meta;

import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import com.pompom.creative.repository.MetaCommentRepository;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Owns public-comment draft, approval, and provider-write admission state. */
@Service
@RequiredArgsConstructor
public class MetaCommentModerationService {

  private final MetaCommentRepository commentRepository;
  private final MetaCommentReplyRepository replyRepository;
  private final MetaCommentReplyGuard replyGuard;

  @Transactional
  public MetaCommentReply createDraft(UUID commentId, String draftText, String idempotencyKey) {
    if (draftText == null || draftText.isBlank()) {
      throw new IllegalArgumentException("draftText is required");
    }
    if (idempotencyKey == null || idempotencyKey.isBlank()) {
      throw new IllegalArgumentException("idempotencyKey is required");
    }
    var existing = replyRepository.findByIdempotencyKey(idempotencyKey);
    if (existing.isPresent()) return existing.get();
    MetaComment comment =
        commentRepository
            .findById(commentId)
            .orElseThrow(() -> new IllegalArgumentException("Comment not found"));
    return replyRepository.save(
        MetaCommentReply.builder()
            .comment(comment)
            .draftText(draftText.trim())
            .idempotencyKey(idempotencyKey)
            .status(MetaCommentReply.Status.DRAFT)
            .build());
  }

  @Transactional
  public MetaCommentReply submitForApproval(UUID replyId) {
    MetaCommentReply reply = findReply(replyId);
    reply.submitForApproval();
    return replyRepository.save(reply);
  }

  @Transactional
  public MetaCommentReply approve(UUID replyId, String reviewer) {
    MetaCommentReply reply = findReply(replyId);
    reply.approve(reviewer);
    return replyRepository.save(reply);
  }

  @Transactional
  public MetaCommentReply reject(UUID replyId, String reviewer, String reason) {
    MetaCommentReply reply = findReply(replyId);
    reply.reject(reviewer, reason);
    return replyRepository.save(reply);
  }

  /** Provider adapters must call this immediately before a public reply write. */
  @Transactional(readOnly = true)
  public MetaCommentReply prepareForProviderSend(UUID replyId) {
    MetaCommentReply reply = findReply(replyId);
    replyGuard.assertAllowed(reply.getComment().getThread().getPlatform());
    if (reply.getStatus() != MetaCommentReply.Status.APPROVED) {
      throw new IllegalStateException("Reply requires human approval before provider send");
    }
    return reply;
  }

  private MetaCommentReply findReply(UUID replyId) {
    return replyRepository
        .findById(replyId)
        .orElseThrow(() -> new IllegalArgumentException("Comment reply not found"));
  }
}
