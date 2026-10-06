package com.pompom.creative.postrender;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PostRenderAssessmentRepository
    extends JpaRepository<PostRenderAssessmentEntity, UUID> {
  Optional<PostRenderAssessmentEntity> findByEvaluationId(UUID evaluationId);
}
