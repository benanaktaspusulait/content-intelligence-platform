package com.pompomhills.intelligence.quality;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

final class ValidationVisualEvidenceProjection {
  private ValidationVisualEvidenceProjection() {}

  static Map<String, Object> project(List<ValidationVisualEvidenceEntity> rows) {
    Map<String, ValidationVisualEvidenceEntity> latest = new LinkedHashMap<>();
    for (ValidationVisualEvidenceEntity row : rows) latest.put(row.getVisualGate(), row);
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("firstFrame", gate(latest.get("FIRST_FRAME")));
    result.put("silhouette", gate(latest.get("SILHOUETTE")));
    result.put("finalVideoEligible", finalVideoEligible(latest));
    return result;
  }

  static boolean finalVideoEligible(List<ValidationVisualEvidenceEntity> rows) {
    Map<String, ValidationVisualEvidenceEntity> latest = new LinkedHashMap<>();
    for (ValidationVisualEvidenceEntity row : rows) latest.put(row.getVisualGate(), row);
    return finalVideoEligible(latest);
  }

  private static boolean finalVideoEligible(Map<String, ValidationVisualEvidenceEntity> latest) {
    ValidationVisualEvidenceEntity first = latest.get("FIRST_FRAME");
    ValidationVisualEvidenceEntity silhouette = latest.get("SILHOUETTE");
    return first != null
        && silhouette != null
        && "PASS".equals(first.getStatus())
        && "PASS".equals(silhouette.getStatus())
        && Objects.equals(first.getEvidenceSetId(), silhouette.getEvidenceSetId())
        && Objects.equals(first.getRenderAssetId(), silhouette.getRenderAssetId())
        && Objects.equals(first.getAssetSha256(), silhouette.getAssetSha256())
        && first.getEvidenceSetId() != null
        && first.getRenderAssetId() != null
        && first.getAssetSha256() != null;
  }

  private static Map<String, Object> gate(ValidationVisualEvidenceEntity row) {
    Map<String, Object> result = new LinkedHashMap<>();
    if (row == null) {
      result.put("status", "PENDING");
      return result;
    }
    result.put("status", row.getStatus());
    result.put("evidenceId", row.getId());
    result.put("evidenceSetId", row.getEvidenceSetId());
    result.put("assetId", row.getRenderAssetId());
    result.put("assetSha256", row.getAssetSha256());
    result.put("verificationId", row.getVerificationId());
    result.put("verifiedAt", row.getVerifiedAt());
    result.put("reason", row.getReason());
    return result;
  }
}
