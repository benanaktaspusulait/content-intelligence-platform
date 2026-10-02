package com.pompomhills.intelligence.creative;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CreativeFingerprintRepository
    extends JpaRepository<CreativeFingerprintEntity, UUID> {
  Optional<CreativeFingerprintEntity> findFirstByVideoIdOrderByCreatedAtDesc(UUID videoId);
}
