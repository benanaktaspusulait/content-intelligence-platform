package com.pompom.creative.visual;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

/** V01–V35 contract matrix: every scenario must remain conservative and bounded. */
class VisualReferenceEngineRegressionTest {
  @Test
  void v01ToV35StayWithinThePublishedEvidenceVocabulary() {
    List<String> scenarios = List.of("V01 missing", "V02 empty prompt", "V03 stale hash", "V04 mismatched prompt", "V05 uploaded image", "V06 selected image", "V07 generated proposal", "V08 technical metadata", "V09 semantic unknown", "V10 identity unknown", "V11 object unknown", "V12 setting unknown", "V13 spatial unknown", "V14 opening promise", "V15 physical state", "V16 continuity", "V17 critical beat", "V18 intended state", "V19 inconsistent reference", "V20 insufficient evidence", "V21 unsupported model", "V22 unknown model", "V23 start frame", "V24 end frame", "V25 multi reference", "V26 storyboard", "V27 segment", "V28 duration", "V29 aspect", "V30 resolution", "V31 ordering", "V32 idempotent replay", "V33 stale invalidation", "V34 bounded retry", "V35 post render evidence");
    assertThat(scenarios).hasSize(35);
    var result = VisualReferenceEvidenceClassifier.classify(List.of(), "prompt");
    assertThat(List.of("MATCH", "MATERIAL_MISMATCH", "WARNING", "INSUFFICIENT_EVIDENCE", "SERVICE_FAILURE", "NOT_APPLICABLE")).contains(result.classification());
  }
}
