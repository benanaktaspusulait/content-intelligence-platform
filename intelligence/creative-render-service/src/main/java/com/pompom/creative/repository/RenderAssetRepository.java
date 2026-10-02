package com.pompom.creative.repository;

import com.pompom.creative.domain.RenderAsset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface RenderAssetRepository extends JpaRepository<RenderAsset, UUID> {

  List<RenderAsset> findByContentIdOrderByCreatedAtDesc(Long contentId);

  Optional<RenderAsset> findByContentIdAndIsCurrentTrue(Long contentId);

  List<RenderAsset> findByRenderJobId(UUID renderJobId);
}
