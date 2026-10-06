package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ValidationVisualEvidenceRepository
    extends JpaRepository<ValidationVisualEvidenceEntity, Long> {
  List<ValidationVisualEvidenceEntity> findByValidationRecordIdOrderBySubmittedAtAscIdAsc(
      Long validationRecordId);

  Optional<ValidationVisualEvidenceEntity> findBySubmissionKey(String submissionKey);
}
