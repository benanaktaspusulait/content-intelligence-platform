package com.pompom.creative.visual;

import java.util.List;

/** Conservative, provider-free classifier for reference evidence. It never infers pixels from metadata. */
public final class VisualReferenceEvidenceClassifier {
  private VisualReferenceEvidenceClassifier() {}

  public static Result classify(List<VisualReferenceAsset> references, String approvedPromptSha256) {
    if (references == null || references.isEmpty()) {
      return new Result("INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE", "No reference image was supplied.");
    }
    boolean promptMismatch = references.stream().anyMatch(r -> approvedPromptSha256 == null || !approvedPromptSha256.equals(r.getPromptSha256()));
    if (promptMismatch) {
      return new Result("INCONSISTENT_REFERENCE", "MATERIAL_MISMATCH", "Reference prompt lineage differs from the approved prompt.");
    }
    boolean stateChange = references.stream().anyMatch(r -> r.getIntendedState() != null && !r.getIntendedState().isBlank());
    if (stateChange) {
      return new Result("INTENDED_STATE_CHANGE", references.size() > 1 ? "INSUFFICIENT_EVIDENCE" : "NOT_APPLICABLE", "State intent is recorded, but semantic cross-image evidence is unavailable.");
    }
    return new Result("INSUFFICIENT_EVIDENCE", references.size() > 1 ? "INSUFFICIENT_EVIDENCE" : "NOT_APPLICABLE", "Technical metadata cannot establish identity, setting, object, or spatial compatibility.");
  }

  public record Result(String classification, String crossReferenceConsistency, String reason) {}
}
