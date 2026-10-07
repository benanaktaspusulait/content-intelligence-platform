package com.pompom.creative.repository;

import com.pompom.creative.domain.MetaCommentReply;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MetaCommentReplyRepository extends JpaRepository<MetaCommentReply, UUID> {
  Optional<MetaCommentReply> findByIdempotencyKey(String idempotencyKey);
}
