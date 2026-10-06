package com.pompom.creative.postrender;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PostRenderEvaluationRepository extends JpaRepository<PostRenderEvaluation, UUID> {
  Optional<PostRenderEvaluation> findTopByRenderAssetIdOrderByCreatedAtDesc(UUID renderAssetId);

  Optional<PostRenderEvaluation> findTopByRenderAsset_RenderJob_IdOrderByCreatedAtDesc(
      UUID renderJobId);

  java.util.List<PostRenderEvaluation>
      findByHumanReviewRequiredTrueAndHumanReviewedAtIsNullOrderByCreatedAtAsc();
}
