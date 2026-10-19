package com.pompomhills.intelligence.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import com.pompomhills.intelligence.video.VideoEntity;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.openpdf.text.pdf.PdfReader;
import org.openpdf.text.pdf.parser.PdfTextExtractor;

class VideoStoryQcPdfTest {
  private VideoDtos.AnalysisStatusResponse status(UUID id) {
    return new VideoDtos.AnalysisStatusResponse(id, true, null, "COMPLETED", null, null, null,
        id, "HIGH_MOTION_EVIDENCE", 89.31, .992, "Measured motion", null, "sampled-visual-motion-v5");
  }
  private String text(byte[] pdf) throws Exception {
    try (var reader = new PdfReader(pdf)) {
      var extractor = new PdfTextExtractor(reader);
      var text = new StringBuilder();
      for (int page = 1; page <= reader.getNumberOfPages(); page++) text.append(extractor.getTextFromPage(page));
      return text.toString().replaceAll("\\s+", " ");
    }
  }
  @Test void missingReviewIsUnknownWithoutBureaucraticCreativeGate() throws Exception {
    var id = UUID.randomUUID();
    String pdf = text(new VideoAnalysisPdfService().render("Actual render", status(id)));
    assertThat(pdf).contains("CREATIVE VIDEO REVIEW", "CREATIVE_REVIEW_NOT_EVALUATED", "UNKNOWN", "Recommendation: NOT_EVALUATED", "owner may publish", id.toString(), "89.3");
    assertThat(pdf).doesNotContain("AUTOMATIC CREATIVE APPROVAL BLOCKED");
    var video = new VideoEntity(id, "bytes", "clip.mp4", "clip.mp4", 15000, 480, 854, 24, .562, "h264", false, null, Instant.now());
    video.setPostRenderQc(Map.of("assetHash", "bytes", "status", "VIDEO_QC_PASS", "creativeStatus", "CREATIVE_QC_PASS"));
    assertThat(video.getPostRenderQc()).containsEntry("creativeStatus", "CREATIVE_REVIEW_NOT_EVALUATED")
        .containsEntry("approvalBlocked", false).containsEntry("automaticPublishingAllowed", false).containsEntry("ownerDecisionRequired", true);
  }
  @Test void ownerReportHasFourQuestionsAndSecondaryMotionWithoutTwelvePrimaryChecks() throws Exception {
    var dimensions = List.of("hook", "engagement", "payoff", "rewatch").stream().map(id -> Map.of("id", id, "rating", "MODERATE")).toList();
    var review = Map.of("status", "CREATIVE_REVIEW_EVALUATED", "recommendation", "REVIEW", "dimensions", dimensions,
        "observations", List.of(Map.of("description", "Synthetic transport observation", "timestampsSeconds", List.of(0, 7, 14))),
        "biggestWeakness", "Synthetic weakness", "actionableRecommendation", "One synthetic action");
    var qc = Map.<String,Object>of("creativeAssessment", review, "storyChecks", List.of(Map.of("id", "hidden-source-check", "status", "FAIL")));
    String pdf = text(new VideoAnalysisPdfService().render("Render", status(UUID.randomUUID()), qc));
    assertThat(pdf).contains("Recommendation: REVIEW", "Synthetic transport observation", "Biggest weakness: Synthetic weakness", "One action: One synthetic action", "Rewatch & sharing potential");
    assertThat(pdf).doesNotContain("hidden-source-check");
    assertThat(pdf.indexOf("Recommendation: REVIEW")).isLessThan(pdf.indexOf("MOTION SCORE"));
  }
}
