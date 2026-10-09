package com.pompom.creative.repository;

import com.pompom.creative.domain.MetaComment;
import java.util.Optional;
import java.util.UUID;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MetaCommentRepository extends JpaRepository<MetaComment, UUID> {
  Optional<MetaComment> findByThreadIdAndExternalCommentId(UUID threadId, String externalCommentId);

  List<MetaComment> findTop100ByOrderByCreatedAtDesc();
}
