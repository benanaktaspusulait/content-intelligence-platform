package com.pompom.creative.postrender;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Human disposition cannot override missing mandatory visual evidence. */
public final class VideoQcGate {
  private VideoQcGate() {}

  public static void requirePass(PostRenderEvaluation evaluation) {
    try {
      var asset = evaluation.getRenderAsset();
      var mapper = new ObjectMapper();
      JsonNode qc = mapper.readTree(evaluation.getEvidenceSnapshot()).path("videoQc");
      JsonNode snapshot = mapper.readTree(asset.getRenderJob().getCreativeContractSnapshot());
      JsonNode authored = snapshot.path("intent").path("visualAcceptanceContract");
      if (authored.isMissingNode()) authored = snapshot.path("visualAcceptanceContract");
      if (authored.isMissingNode()) authored = snapshot;
      if (!"STORY_QC_PASS".equals(qc.path("storyStatus").asText())
          || !"VIDEO_QC_PASS".equals(qc.path("status").asText())
          || !qc.path("approvalBlocked").isBoolean() || qc.path("approvalBlocked").asBoolean()
          || asset.getSha256() == null || !asset.getSha256().equals(qc.path("assetHash").asText())
          || authored.isMissingNode() || !authored.equals(qc.path("contract"))
          || qc.path("frames").isEmpty() || qc.path("motionWindows").isEmpty())
        throw new IllegalStateException("Mandatory story-aware video QC has not passed; inspect timestamped videoQc evidence");
      JsonNode evaluated = qc.has("evaluatedContract") ? qc.path("evaluatedContract") : authored;
      if (!"FULL_VIDEO".equals(evaluated.path("scope").asText()))
        throw new IllegalStateException("Full story evaluation is required");
      if (!evaluated.path("requirements").isArray() || evaluated.path("requirements").isEmpty())
        throw new IllegalStateException("Visual acceptance requirements are missing");
      for (JsonNode requirement : evaluated.path("requirements")) {
        if (!requirement.path("mandatory").asBoolean(true)) continue;
        boolean passed = false;
        for (JsonNode check : qc.path("checks")) {
          if (requirement.path("id").asText().equals(check.path("id").asText())
              && "PASS".equals(check.path("status").asText())) passed = true;
        }
        if (!passed) throw new IllegalStateException("Mandatory visual check has not passed: " + requirement.path("id").asText());
      }
    } catch (IllegalStateException error) {
      throw error;
    } catch (Exception error) {
      throw new IllegalStateException("Mandatory story-aware video QC evidence is missing or invalid", error);
    }
  }
}
