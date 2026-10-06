package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

/** Repository for quality validation history. */
@Repository
public interface QualityValidationRepository extends JpaRepository<QualityValidationEntity, Long> {

  Optional<QualityValidationEntity> findByValidationRunId(UUID validationRunId);

  /** Latest stored report for a linked content/prompt version. */
  Optional<QualityValidationEntity>
      findFirstByContentIdAndPromptVersionIdAndReportJsonIsNotNullOrderByIdDesc(
          Long contentId, Long promptVersionId);

  /** Latest stored report for an unlinked prompt, identified by its text fingerprint. */
  Optional<QualityValidationEntity>
      findFirstByPromptFingerprintAndContentIdIsNullAndReportJsonIsNotNullOrderByIdDesc(
          String promptFingerprint);

  /**
   * Find all validations for a specific prompt ordered by date.
   *
   * @param promptId Prompt ID
   * @return List of validations
   */
  List<QualityValidationEntity> findByPromptIdOrderByCreatedAtDesc(Long promptId);

  /**
   * Count validations by status.
   *
   * @param status Status string (RENDER_READY, BLOCKED, NEEDS_REVISION)
   * @return Count
   */
  long countByStatus(String status);

  /**
   * Calculate average score across all validations.
   *
   * @return Average score or null if no validations
   */
  @Query("SELECT AVG(v.overallScore) FROM QualityValidationEntity v")
  Double averageScore();

  /**
   * Find recent validations for dashboard.
   *
   * @return Recent validations
   */
  @Query("SELECT v FROM QualityValidationEntity v ORDER BY v.createdAt DESC LIMIT 100")
  List<QualityValidationEntity> findRecentValidations();
}
