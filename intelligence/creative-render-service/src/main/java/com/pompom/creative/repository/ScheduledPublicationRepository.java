package com.pompom.creative.repository;

import com.pompom.creative.domain.ScheduleStatus;
import com.pompom.creative.domain.ScheduledPublication;
import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ScheduledPublicationRepository extends JpaRepository<ScheduledPublication, UUID> {

  List<ScheduledPublication> findByIsExecutedFalse();

  List<ScheduledPublication> findByScheduleStatus(ScheduleStatus status);

  List<ScheduledPublication> findByIsExecutedFalseAndScheduledAtBefore(Instant before);

  List<ScheduledPublication> findByPlatformAndIsExecutedFalse(PlatformType platform);

  List<ScheduledPublication> findAllByOrderByScheduledAtAsc();

  long countByIsExecutedFalse();

  long countByIsExecutedTrue();
}
