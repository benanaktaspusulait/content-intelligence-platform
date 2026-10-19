package com.pompom.creative.postrender;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Creative advice never substitutes for owner authority or verified media integrity. */
public final class VideoQcGate {
  private VideoQcGate() {}

  /** Publication requires an audited explicit owner decision, even after a PUBLISH recommendation. */
  public static void requirePass(PostRenderEvaluation evaluation) {
    requireTechnicalIntegrity(evaluation);
    if (!"APPROVED".equals(evaluation.getHumanDecision()) || evaluation.getHumanReviewedAt() == null)
      throw new IllegalStateException("Explicit owner publication approval is required; creative advice cannot authorize publishing");
  }

  /** May be called before recording owner approval, regardless of creative recommendation. */
  public static void requireTechnicalIntegrity(PostRenderEvaluation evaluation) {
    try {
      var asset = evaluation.getRenderAsset();
      if (asset == null || !Boolean.TRUE.equals(asset.getMediaVerified()) || asset.getSha256() == null
          || Boolean.TRUE.equals(asset.getQuarantined()) || Boolean.TRUE.equals(asset.getIsMock()))
        throw new IllegalStateException("Verified, non-quarantined media is required");
      JsonNode evidence = new ObjectMapper().readTree(evaluation.getEvidenceSnapshot());
      JsonNode qc = evidence.path("videoQc");
      if (qc.hasNonNull("assetHash") && !asset.getSha256().equals(qc.path("assetHash").asText()))
        throw new IllegalStateException("QC evidence belongs to different video bytes");
      if ("TECHNICAL_QC_FAIL".equals(qc.path("technicalStatus").asText()))
        throw new IllegalStateException("Technical video corruption cannot be overridden by creative approval");
      for (JsonNode check : qc.path("checks")) {
        if (java.util.Set.of("stream_decode", "asset_unchanged", "pixel_inspection").contains(check.path("id").asText())
            && "FAIL".equals(check.path("status").asText()))
          throw new IllegalStateException("Mandatory technical integrity check failed");
      }
      JsonNode technical = evidence.path("technical");
      for (String key : java.util.List.of("mediaReadable", "checksumVerified")) {
        if (technical.path(key).isBoolean() && !technical.path(key).asBoolean())
          throw new IllegalStateException("Mandatory media integrity evidence failed");
      }
      for (String key : java.util.List.of("durationMs", "width", "height")) {
        if (technical.path(key).isNumber() && technical.path(key).asDouble() <= 0)
          throw new IllegalStateException("Invalid video metadata");
      }
      // Platform guards, account authorization, quarantine and dispatch checksum verification remain independent.
    } catch (IllegalStateException error) {
      throw error;
    } catch (Exception error) {
      throw new IllegalStateException("Media integrity evidence is invalid", error);
    }
  }
}
