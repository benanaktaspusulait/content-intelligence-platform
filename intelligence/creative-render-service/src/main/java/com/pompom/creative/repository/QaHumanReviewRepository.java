package com.pompom.creative.repository;

import com.pompom.creative.domain.QaHumanReview;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QaHumanReviewRepository extends JpaRepository<QaHumanReview, UUID> {

  List<QaHumanReview> findByRenderQaResultIdOrderByCreatedAtDesc(UUID renderQaResultId);

  List<QaHumanReview> findByPostRenderEvaluationIdOrderByCreatedAtDesc(UUID evaluationId);
}
