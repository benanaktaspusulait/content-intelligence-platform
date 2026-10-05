package com.pompom.creative.repository;

import com.pompom.creative.domain.CaptionVersion;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CaptionVersionRepository extends JpaRepository<CaptionVersion, UUID> {
  List<CaptionVersion> findByRenderAssetIdOrderByCreatedAtDesc(UUID renderAssetId);
}
