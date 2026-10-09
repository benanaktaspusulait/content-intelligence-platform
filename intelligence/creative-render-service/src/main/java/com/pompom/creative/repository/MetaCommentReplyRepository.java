package com.pompom.creative.repository;

import com.pompom.creative.domain.MetaCommentReply;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface MetaCommentReplyRepository extends JpaRepository<MetaCommentReply, UUID> {
  Optional<MetaCommentReply> findByIdempotencyKey(String idempotencyKey);

  @Lock(LockModeType.PESSIMISTIC_WRITE)
  @Query("select reply from MetaCommentReply reply where reply.id = :replyId")
  Optional<MetaCommentReply> findByIdForUpdate(@Param("replyId") UUID replyId);

  List<MetaCommentReply> findTop100ByOrderByCreatedAtDesc();
}
