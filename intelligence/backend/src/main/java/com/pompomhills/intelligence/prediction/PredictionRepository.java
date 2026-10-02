package com.pompomhills.intelligence.prediction;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PredictionRepository extends JpaRepository<PredictionEntity, UUID> {
  List<PredictionEntity> findByVideoIdOrderByCreatedAtDesc(UUID videoId);

  List<PredictionEntity> findAllByOrderByCreatedAtDesc();
}
