package com.pompom.creative.repository;

import com.pompom.creative.domain.OpenArtCreditLog;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface OpenArtCreditLogRepository extends JpaRepository<OpenArtCreditLog, UUID> {

  List<OpenArtCreditLog> findByRenderJobIdOrderByLoggedAtAsc(UUID renderJobId);

  List<OpenArtCreditLog> findByLoggedAtAfter(Instant after);

  List<OpenArtCreditLog> findByLoggedAtBetween(Instant start, Instant end);

  Optional<OpenArtCreditLog> findFirstByOpenartJobIdAndOperation(
      String openartJobId, String operation);

  @Query(
      "select l from OpenArtCreditLog l where l.renderJob.id = :renderJobId "
          + "and l.operation = :operation and l.openartJobId is null")
  Optional<OpenArtCreditLog> findUnassignedReservation(
      @Param("renderJobId") UUID renderJobId, @Param("operation") String operation);
}
