package com.pompomhills.intelligence.quality;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public final class VisualEvidenceDtos {
  private VisualEvidenceDtos() {}

  public record VisualEvidenceRequest(
      Long contentId,
      Long promptVersionId,
      String promptSha256,
      String gate,
      String status,
      UUID evidenceSetId,
      UUID renderJobId,
      UUID renderAssetId,
      String assetType,
      String assetRelativePath,
      String assetSha256,
      Map<String, Object> provenance,
      String reason,
      String verificationId,
      Instant verifiedAt,
      String submissionKey) {}

  public record VisualEvidenceResponse(
      long validationRecordId,
      long visualEvidenceId,
      String gate,
      String status,
      boolean firstFrameEligible,
      boolean finalVideoEligible,
      Map<String, Object> visualEvidence,
      boolean created) {}
}
