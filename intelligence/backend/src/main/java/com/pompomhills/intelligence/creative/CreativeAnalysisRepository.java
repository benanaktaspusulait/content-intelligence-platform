package com.pompomhills.intelligence.creative;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CreativeAnalysisRepository extends JpaRepository<CreativeAnalysisEntity, UUID> {
  Optional<CreativeAnalysisEntity> findFirstByVideoIdOrderByCreatedAtDesc(UUID videoId);

  Optional<CreativeAnalysisEntity> findFirstByVideoIdAndAnalysisVersionOrderByCreatedAtDesc(
      UUID videoId, String analysisVersion);

  boolean existsByVideoId(UUID videoId);

  boolean existsByVideoIdAndAnalysisVersion(UUID videoId, String analysisVersion);
}
