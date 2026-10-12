package com.pompom.creative.repository;

import com.pompom.creative.domain.CaptionVersion;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CaptionVersionRepository extends JpaRepository<CaptionVersion, UUID> {
  List<CaptionVersion> findByRenderAssetIdOrderByCreatedAtDesc(UUID renderAssetId);

  @Query("SELECT cv FROM CaptionVersion cv "
      + "JOIN com.pompom.creative.domain.RenderAsset ra ON cv.renderAssetId = ra.id "
      + "WHERE ra.videoId = :videoId "
      + "ORDER BY cv.createdAt DESC")
  List<CaptionVersion> findByVideoIdOrderByCreatedAtDesc(@Param("videoId") UUID videoId);
}
