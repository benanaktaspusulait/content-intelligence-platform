package com.pompom.creative.trajectory;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface TrajectoryAnalysisRepository extends JpaRepository<TrajectoryAnalysis, UUID> {

  Optional<TrajectoryAnalysis> findByPublicationJobId(UUID publicationJobId);

  List<TrajectoryAnalysis> findByTrajectoryShape(TrajectoryAnalysis.TrajectoryShape shape);

  @Query(
      "SELECT t FROM TrajectoryAnalysis t WHERE t.waveCount >= :minWaves "
          + "ORDER BY t.waveCount DESC")
  List<TrajectoryAnalysis> findMultiWaveTrajectories(@Param("minWaves") int minWaves);

  @Query(
      "SELECT t FROM TrajectoryAnalysis t WHERE t.tailStrength >= :minStrength "
          + "ORDER BY t.tailStrength DESC")
  List<TrajectoryAnalysis> findStrongTailTrajectories(
      @Param("minStrength") java.math.BigDecimal minStrength);

  @Query(
      "SELECT t FROM TrajectoryAnalysis t WHERE t.velocityFirst24H >= :minVelocity "
          + "ORDER BY t.velocityFirst24H DESC")
  List<TrajectoryAnalysis> findHighVelocityTrajectories(
      @Param("minVelocity") java.math.BigDecimal minVelocity);
}
