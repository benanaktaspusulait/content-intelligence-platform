package com.pompom.creative.repository;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.domain.RenderJob.RenderJobStatus;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface RenderJobRepository extends JpaRepository<RenderJob, UUID> {

  java.util.Optional<RenderJob> findByIdempotencyKey(String idempotencyKey);

  List<RenderJob> findByContentIdOrderByQueuedAtDesc(Long contentId);

  List<RenderJob> findByContentIdOrderByCreatedAtDesc(Long contentId);

  List<RenderJob> findByStatus(RenderJobStatus status);

  int countByStatus(RenderJobStatus status);

  List<RenderJob> findByStatusOrderByQueuedAtAsc(RenderJobStatus status);
}
