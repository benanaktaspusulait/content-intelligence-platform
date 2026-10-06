package com.pompomhills.intelligence.quality;

import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Read side of validation history: returns the latest stored analysis for a prompt. */
@Service
public class QualityValidationHistoryService {

  private final QualityValidationRepository repository;

  public QualityValidationHistoryService(QualityValidationRepository repository) {
    this.repository = repository;
  }

  @Transactional(readOnly = true)
  public Optional<StoredValidationResponse> findLatest(LatestValidationRequest request) {
    boolean linked = request.contentId() != null && request.promptVersionId() != null;

    Optional<QualityValidationEntity> entity;
    if (linked) {
      entity =
          repository
              .findFirstByContentIdAndPromptVersionIdAndReportJsonIsNotNullOrderByIdDesc(
                  request.contentId(), request.promptVersionId());
    } else {
      if (request.prompt() == null || request.prompt().isBlank()) {
        throw new IllegalArgumentException(
            "Either contentId and promptVersionId, or prompt text, is required");
      }
      entity =
          repository
              .findFirstByPromptFingerprintAndContentIdIsNullAndReportJsonIsNotNullOrderByIdDesc(
                  QualityReportSnapshots.fingerprint(request.prompt()));
    }

    return entity.flatMap(
        found -> {
          QualityReportDto report = QualityReportSnapshots.fromJson(found.getReportJson());
          return report == null
              ? Optional.empty()
              : Optional.of(
                  new StoredValidationResponse(found.getId(), report, found.getCreatedAt()));
        });
  }
}
