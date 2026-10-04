package com.pompom.creative.repository;

import com.pompom.creative.domain.PublicationAttempt;
import com.pompom.creative.domain.PublicationExecutionStage;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PublicationAttemptRepository extends JpaRepository<PublicationAttempt, UUID> {
  List<PublicationAttempt> findByPublicationJobIdOrderByAttemptNumberAsc(UUID publicationJobId);

  List<PublicationAttempt> findByStageAndLeaseExpiresAtBefore(
      PublicationExecutionStage stage, Instant cutoff);
}
