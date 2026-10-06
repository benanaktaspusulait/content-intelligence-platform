package com.pompom.creative.postrender;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PostRenderRuleResultRepository
    extends JpaRepository<PostRenderRuleResultEntity, UUID> {
  List<PostRenderRuleResultEntity> findByEvaluationIdOrderByRuleId(UUID evaluationId);
}
