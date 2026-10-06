package com.pompom.creative.repository;

import com.pompom.creative.domain.RenderAsset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface RenderAssetRepository extends JpaRepository<RenderAsset, UUID> {

  List<RenderAsset> findByContentIdOrderByCreatedAtDesc(Long contentId);

  Optional<RenderAsset> findByContentIdAndIsCurrentTrue(Long contentId);

  List<RenderAsset> findByRenderJobId(UUID renderJobId);

  @Modifying
  @Query(
      "update RenderAsset a set a.isCurrent = false "
          + "where a.contentId = :contentId and a.assetType = :assetType and a.isCurrent = true")
  int clearCurrentForContentAndType(
      @Param("contentId") Long contentId, @Param("assetType") RenderAsset.AssetType assetType);
}
