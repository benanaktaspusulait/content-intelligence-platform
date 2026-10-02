package com.pompom.creative.analytics;

import com.pompom.creative.oauth.PlatformType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface PerformancePredictionRepository
    extends JpaRepository<PerformancePrediction, UUID> {

  /** Find predictions by content ID. */
  List<PerformancePrediction> findByContentId(Long contentId);

  /** Find prediction by publication job ID. */
  Optional<PerformancePrediction> findByPublicationJobId(UUID publicationJobId);

  /** Find predictions by platform. */
  List<PerformancePrediction> findByPlatformOrderByPredictedAtDesc(PlatformType platform);

  /** Find high-confidence predictions. */
  @Query(
      "SELECT p FROM PerformancePrediction p WHERE p.confidenceLevel >= :minConfidence "
          + "ORDER BY p.predictedAt DESC")
  List<PerformancePrediction> findHighConfidencePredictions(double minConfidence);

  /** Find predictions with high viral potential. */
  @Query(
      "SELECT p FROM PerformancePrediction p WHERE p.viralPotential >= :threshold "
          + "ORDER BY p.viralPotential DESC")
  List<PerformancePrediction> findHighViralPotential(double threshold);
}
