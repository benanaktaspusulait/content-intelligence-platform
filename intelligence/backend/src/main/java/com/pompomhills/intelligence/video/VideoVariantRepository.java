package com.pompomhills.intelligence.video;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoVariantRepository extends JpaRepository<VideoVariantEntity, UUID> {
  List<VideoVariantEntity> findAllByVideoId(UUID videoId);

  Optional<VideoVariantEntity> findByIdAndVideoId(UUID id, UUID videoId);

  Optional<VideoVariantEntity> findByGeneratedPath(String generatedPath);
}
