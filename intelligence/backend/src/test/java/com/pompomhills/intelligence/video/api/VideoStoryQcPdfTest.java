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
  @Test void excellentMotionCannotHideUnevaluatedStoryInPdfOrImportedVideo() throws Exception {
    var id = UUID.randomUUID();
    var status = new VideoDtos.AnalysisStatusResponse(id, true, null, "COMPLETED", null, null, null,
        id, "HIGH_MOTION_EVIDENCE", 89.31, .992, "Measured motion", null, "sampled-visual-motion-v5");
    byte[] pdf = new VideoAnalysisPdfService().render("Actual render", status);
    try (var reader = new PdfReader(pdf)) {
      var extractor = new PdfTextExtractor(reader);
      var text = new StringBuilder();
      for (int page = 1; page <= reader.getNumberOfPages(); page++) text.append(extractor.getTextFromPage(page));
      assertThat(text.toString()).contains("STORY_QC_NOT_EVALUATED", "AUTOMATIC CREATIVE APPROVAL BLOCKED", id.toString(), "89.3");
    }
    var video = new VideoEntity(id, "bytes", "clip.mp4", "clip.mp4", 15000, 480, 854, 24,
        .562, "h264", false, null, Instant.now());
    video.setPostRenderQc(Map.of("assetHash", "bytes", "status", "VIDEO_QC_PASS", "approvalBlocked", false));
    assertThat(video.getPostRenderQc()).containsEntry("storyStatus", "STORY_QC_NOT_EVALUATED").containsEntry("approvalBlocked", true);
  }

  @Test void pdfIncludesBoundStoryFailureAndTimestampEvidence() throws Exception {
    var id = UUID.randomUUID();
    var status = new VideoDtos.AnalysisStatusResponse(id, true, null, "COMPLETED", null, null, null,
        id, "HIGH_MOTION_EVIDENCE", 89.31, .992, "Measured motion", null, "sampled-visual-motion-v5");
    var qc = Map.<String,Object>of("storyStatus", "STORY_QC_FAIL", "status", "VIDEO_QC_FAIL", "approvalBlocked", true,
        "storyBinding", Map.of("storyId", "authored-story", "storyRevision", "3"),
        "storyChecks", List.of(Map.of("id", "timed-event", "status", "FAIL", "window", List.of(0, 2),
          "timestampsSeconds", List.of(0, 1, 2), "reason", "Synthetic transport test only")));
    try (var reader = new PdfReader(new VideoAnalysisPdfService().render("Render", status, qc))) {
      var extractor = new PdfTextExtractor(reader);
      var text = new StringBuilder();
      for (int page = 1; page <= reader.getNumberOfPages(); page++) text.append(extractor.getTextFromPage(page));
      assertThat(text.toString()).contains("STORY_QC_FAIL", "authored-story", "timed-event", "Synthetic transport test only", "[0, 1, 2]");
    }
  }
}
