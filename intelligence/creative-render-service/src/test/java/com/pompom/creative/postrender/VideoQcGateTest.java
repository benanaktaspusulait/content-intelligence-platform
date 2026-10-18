package com.pompom.creative.postrender;

import static org.assertj.core.api.Assertions.*;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

public class VideoQcGateTest {
  public static PostRenderEvaluation evaluation(String status, String hash) {
    String contract = "{\"scope\":\"FULL_VIDEO\",\"requirements\":[{\"id\":\"event\",\"mandatory\":true}]}";
    var job = RenderJob.builder().creativeContractSnapshot("{\"intent\":{\"visualAcceptanceContract\":" + contract + "}}").build();
    var asset = RenderAsset.builder().id(UUID.randomUUID()).renderJob(job).sha256("checksum")
        .assetType(RenderAsset.AssetType.VIDEO).build();
    var evidence = "{\"videoQc\":{\"status\":\"" + status + "\",\"assetHash\":\"" + hash
        + "\",\"storyStatus\":\"STORY_QC_PASS\",\"approvalBlocked\":false,\"contract\":" + contract
        + ",\"frames\":[{\"timestampSeconds\":0}],\"motionWindows\":[{}],\"checks\":[{\"id\":\"event\",\"status\":\"PASS\"}]}}";
    return PostRenderEvaluation.builder().renderAsset(asset).evidenceSnapshot(evidence)
        .overallDecision(PostRenderDecision.PASS).build();
  }

  @ParameterizedTest
  @ValueSource(strings = {"VIDEO_QC_FAIL", "VIDEO_QC_UNCERTAIN", "VIDEO_QC_NOT_EVALUATED", "PASS", ""})
  void nonpassingMandatoryQcCannotBeApproved(String status) {
    assertThatThrownBy(() -> VideoQcGate.requirePass(evaluation(status, "checksum")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test void exactAssetEvidenceCanPass() {
    assertThatCode(() -> VideoQcGate.requirePass(evaluation("VIDEO_QC_PASS", "checksum"))).doesNotThrowAnyException();
  }

  @Test void differentVideoBytesCannotReuseAPass() {
    assertThatThrownBy(() -> VideoQcGate.requirePass(evaluation("VIDEO_QC_PASS", "other-bytes")))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test void summaryPassCannotHideAMissingMandatoryCheck() {
    var e = evaluation("VIDEO_QC_PASS", "checksum");
    var forged = PostRenderEvaluation.builder().renderAsset(e.getRenderAsset())
        .evidenceSnapshot(e.getEvidenceSnapshot().replace("\"checks\":[{\"id\":\"event\",\"status\":\"PASS\"}]", "\"checks\":[]")).build();
    assertThatThrownBy(() -> VideoQcGate.requirePass(forged)).isInstanceOf(IllegalStateException.class);
  }
  @Test void legacyMotionPassWithoutStoryStatusCannotApprove() {
    var e = evaluation("VIDEO_QC_PASS", "checksum");
    var legacy = PostRenderEvaluation.builder().renderAsset(e.getRenderAsset())
        .evidenceSnapshot(e.getEvidenceSnapshot().replace("STORY_QC_PASS", "STORY_QC_NOT_EVALUATED")).build();
    assertThatThrownBy(() -> VideoQcGate.requirePass(legacy)).isInstanceOf(IllegalStateException.class);
  }

}
