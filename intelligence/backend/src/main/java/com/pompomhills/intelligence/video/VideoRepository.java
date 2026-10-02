package com.pompomhills.intelligence.video;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoRepository extends JpaRepository<VideoEntity, UUID> {
  Optional<VideoEntity> findByContentHash(String contentHash);

  List<VideoEntity> findAllByRelativePathIn(Collection<String> relativePaths);

  Page<VideoEntity> findByStatus(VideoStatus status, Pageable pageable);
}
