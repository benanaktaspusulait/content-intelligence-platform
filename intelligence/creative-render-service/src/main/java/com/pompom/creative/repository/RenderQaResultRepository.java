package com.pompom.creative.repository;

import com.pompom.creative.domain.RenderQaResult;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface RenderQaResultRepository extends JpaRepository<RenderQaResult, UUID> {

  Optional<RenderQaResult> findByRenderAssetId(UUID renderAssetId);

  Optional<RenderQaResult> findTopByRenderAssetIdOrderByCreatedAtDesc(UUID renderAssetId);

  Optional<RenderQaResult> findTopByRenderAsset_RenderJob_IdOrderByCreatedAtDesc(UUID renderJobId);

  List<RenderQaResult> findByRequiresHumanReviewTrueAndHumanReviewedAtIsNullOrderByCreatedAtAsc();
}
