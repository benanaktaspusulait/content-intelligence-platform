package com.pompom.creative.visual;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VisualReferenceAssetRepository extends JpaRepository<VisualReferenceAsset, UUID> {
  List<VisualReferenceAsset> findByPlanIdOrderByCreatedAtAsc(UUID planId);
}
