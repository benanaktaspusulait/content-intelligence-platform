package com.pompom.creative.visual;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

class VisualReferenceEvidenceClassifierTest {
  @Test void reportsInsufficientEvidenceWithoutReferences() {
    assertThat(VisualReferenceEvidenceClassifier.classify(List.of(), "p").classification()).isEqualTo("INSUFFICIENT_EVIDENCE");
  }

  @Test void reportsInconsistentReferenceForPromptLineageMismatch() {
    VisualReferenceAsset asset = VisualReferenceAsset.builder().promptSha256("old").build();
    assertThat(VisualReferenceEvidenceClassifier.classify(List.of(asset), "new").classification()).isEqualTo("INCONSISTENT_REFERENCE");
  }

  @Test void recordsIntendedStateChangeWithoutClaimingSemanticMatch() {
    VisualReferenceAsset asset = VisualReferenceAsset.builder().promptSha256("p").intendedState("reveal").build();
    var result = VisualReferenceEvidenceClassifier.classify(List.of(asset), "p");
    assertThat(result.classification()).isEqualTo("INTENDED_STATE_CHANGE");
    assertThat(result.crossReferenceConsistency()).isEqualTo("NOT_APPLICABLE");
  }
}
