package com.pompom.creative.performance;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface PerformanceClassificationRepository
    extends JpaRepository<PerformanceClassification, UUID> {

  Optional<PerformanceClassification> findByPublicationJobId(UUID publicationJobId);

  List<PerformanceClassification> findByCategory(
      PerformanceClassification.PerformanceCategory category);

  @Query(
      "SELECT c FROM PerformanceClassification c WHERE c.category IN :categories "
          + "ORDER BY c.finalViews DESC")
  List<PerformanceClassification> findByCategories(
      @Param("categories") List<PerformanceClassification.PerformanceCategory> categories);

  @Query(
      "SELECT c FROM PerformanceClassification c WHERE "
          + "c.category IN ('BREAKOUT', 'DELAYED_BREAKOUT', 'MULTI_WAVE', 'PERSISTENT_WINNER', 'EVERGREEN_BREAKOUT') "
          + "ORDER BY c.finalViews DESC")
  List<PerformanceClassification> findWinners();

  @Query("SELECT COUNT(c) FROM PerformanceClassification c WHERE c.category = :category")
  Long countByCategory(@Param("category") PerformanceClassification.PerformanceCategory category);

  @Query("SELECT c.category, COUNT(c) FROM PerformanceClassification c " + "GROUP BY c.category")
  List<Object[]> getCategoryDistribution();
}
