package com.pompom.creative.repository;

import com.pompom.creative.domain.OpenArtCreditLog;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface OpenArtCreditLogRepository extends JpaRepository<OpenArtCreditLog, UUID> {

  List<OpenArtCreditLog> findByRenderJobIdOrderByLoggedAtAsc(UUID renderJobId);

  List<OpenArtCreditLog> findByLoggedAtAfter(Instant after);

  List<OpenArtCreditLog> findByLoggedAtBetween(Instant start, Instant end);
}
