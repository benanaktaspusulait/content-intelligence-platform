package com.pompomhills.intelligence.video;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoPathAliasRepository extends JpaRepository<VideoPathAliasEntity, UUID> {
  Optional<VideoPathAliasEntity> findByRelativePath(String relativePath);

  List<VideoPathAliasEntity> findAllByVideoId(UUID videoId);
}
