package com.pompom.creative.benchmark;

import com.pompom.creative.performance.PerformanceClassification;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface WinnerEntryRepository extends JpaRepository<WinnerEntry, UUID> {

  Optional<WinnerEntry> findByPublicationJobId(UUID publicationJobId);

  List<WinnerEntry> findByWinnerTier(WinnerEntry.WinnerTier tier);

  List<WinnerEntry> findByPerformanceCategory(
      PerformanceClassification.PerformanceCategory category);

  @Query("SELECT w FROM WinnerEntry w ORDER BY w.benchmarkScore DESC")
  List<WinnerEntry> findAllByBenchmarkScore();

  @Query(
      "SELECT w FROM WinnerEntry w WHERE w.winnerTier = :tier " + "ORDER BY w.benchmarkScore DESC")
  List<WinnerEntry> findTopPerformersByTier(@Param("tier") WinnerEntry.WinnerTier tier);

  @Query(
      "SELECT w FROM WinnerEntry w WHERE w.benchmarkScore >= :minScore "
          + "ORDER BY w.benchmarkScore DESC")
  List<WinnerEntry> findHighScorers(@Param("minScore") BigDecimal minScore);

  @Query(
      "SELECT w FROM WinnerEntry w WHERE w.trajectoryShape = :shape "
          + "ORDER BY w.benchmarkScore DESC")
  List<WinnerEntry> findByTrajectoryShape(@Param("shape") String shape);

  @Query("SELECT COUNT(w) FROM WinnerEntry w")
  long countWinners();

  @Query("SELECT AVG(w.benchmarkScore) FROM WinnerEntry w WHERE w.winnerTier = :tier")
  BigDecimal getAverageBenchmarkScoreByTier(@Param("tier") WinnerEntry.WinnerTier tier);
}
