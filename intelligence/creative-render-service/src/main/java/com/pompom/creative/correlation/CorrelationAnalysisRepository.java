package com.pompom.creative.correlation;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface CorrelationAnalysisRepository extends JpaRepository<CorrelationAnalysis, UUID> {

  Optional<CorrelationAnalysis> findFirstByOrderByAnalyzedAtDesc();

  List<CorrelationAnalysis> findTop10ByOrderByAnalyzedAtDesc();

  @Query(
      "SELECT c FROM CorrelationAnalysis c WHERE c.sampleSize >= :minSampleSize "
          + "ORDER BY c.analyzedAt DESC")
  List<CorrelationAnalysis> findReliableAnalyses(int minSampleSize);
}
