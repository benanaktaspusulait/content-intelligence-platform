package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.content.ContentPromptSnapshot;
import com.pompomhills.intelligence.quality.QualityMlClient;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import java.util.Map;
import org.junit.jupiter.api.Test;

class WorkflowServiceTest {
  @Test
  void linkedReviewUsesStoredPromptAndCannotBeOverriddenByOptions() {
    var content = mock(ContentPromptQueryService.class);
    when(content.load(1L, 2L))
        .thenReturn(
            new ContentPromptSnapshot(
                "v1", 1, "Title", "REEL", "DRAFT", 2, 1, "Stored prompt", "{}", "a".repeat(64)));
    var ml = mock(QualityMlClient.class);
    when(ml.workflow(eq("review"), anyMap()))
        .thenAnswer(
            call -> Map.<String, Object>of("bindingHash", "binding", "input", call.getArgument(1)));
    var service =
        new WorkflowService(
            content,
            ml,
            mock(MediaContentService.class),
            mock(VideoService.class),
            new ObjectMapper(),
            null,
            null);
    var result =
        service.runReview(
            new WorkflowService.ReviewRequest(
                1L,
                2L,
                "Wrong request prompt",
                "draft",
                Map.of("profile", "post-family-v1", "prompt", "malicious override")),
            false);
    Map<?, ?> input = (Map<?, ?>) result.get("input");
    assertThat(input.get("prompt")).isEqualTo("Stored prompt");
    assertThat(input.get("sourceVersion")).isEqualTo("2");
  }

  @Test
  void explicitPostFamilyProfileIsRequired() {
    var service = new WorkflowService(null, null, null, null, new ObjectMapper(), null, null);
    assertThatThrownBy(
            () ->
                service.runReview(
                    new WorkflowService.ReviewRequest(null, null, "Prompt", "draft", Map.of()),
                    false))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void finalAdmissionNeverAcceptsLegacyReadinessOrChangedBinding() {
    var review =
        Map.<String, Object>of(
            "bindingHash",
            "binding",
            "family8",
            Map.of("renderAuthorization", Map.of("status", "RENDER_READY")));
    assertThatThrownBy(() -> WorkflowService.requireAuthorized(review, "binding"))
        .isInstanceOf(IllegalStateException.class);
    var authorized =
        Map.<String, Object>of(
            "bindingHash",
            "binding",
            "family8",
            Map.of("renderAuthorization", Map.of("status", "AUTHORIZED")));
    assertThatThrownBy(() -> WorkflowService.requireAuthorized(authorized, "changed"))
        .isInstanceOf(IllegalStateException.class);
    assertThatCode(() -> WorkflowService.requireAuthorized(authorized, "binding"))
        .doesNotThrowAnyException();
  }

  @Test
  void admissionRechecksGeneratorDurationFrameHashAndFinalBinding() {
    var service = spy(new WorkflowService(null, null, null, null, new ObjectMapper(), null, null));
    var id = java.util.UUID.randomUUID();
    var stored =
        Map.<String, Object>of(
            "contentId",
            1L,
            "promptVersionId",
            2L,
            "bindingHash",
            "binding",
            "boundRequest",
            Map.of("profile", "post-family-v1"),
            "family8",
            Map.of("renderAuthorization", Map.of("status", "AUTHORIZED")));
    var fresh = new java.util.LinkedHashMap<String, Object>(stored);
    fresh.put(
        "generation",
        Map.of(
            "capabilityStatus",
            "SUPPORTED",
            "mode",
            "image2video",
            "apiModelId",
            "verified-model",
            "supportedRenderDuration",
            6,
            "settings",
            Map.of(
                "aspectRatio",
                "9:16",
                "resolution",
                "480p",
                "startFrame",
                Map.of("id", "library/frame.png")),
            "segments",
            java.util.List.of()));
    fresh.put(
        "boundRequest",
        Map.of(
            "authorizationEvidence",
            Map.of("visualEvidence", Map.of("firstFrame", Map.of("assetSha256", "a".repeat(64)))),
            "references",
            java.util.List.of(
                Map.of(
                    "kind",
                    "FIRST_FRAME",
                    "status",
                    "VERIFIED",
                    "relativePath",
                    "library/frame.png",
                    "sha256",
                    "a".repeat(64)))));
    doReturn(stored).when(service).get(id);
    doReturn(fresh).when(service).runReview(any(), eq(false));
    var queued =
        new java.util.LinkedHashMap<String, Object>(
            Map.of(
                "contentId",
                1,
                "promptVersionId",
                2,
                "bindingHash",
                "binding",
                "model",
                "verified-model",
                "settings",
                Map.of(
                    "durationSeconds",
                    6,
                    "aspectRatio",
                    "9:16",
                    "firstFrameImageId",
                    "library/frame.png")));
    assertThat(service.admission(id, queued)).containsEntry("renderAuthorization", "AUTHORIZED");
    queued.put("model", "different-model");
    assertThatThrownBy(() -> service.admission(id, queued))
        .isInstanceOf(IllegalStateException.class);
    queued.put("model", "verified-model");
    queued.put(
        "settings",
        Map.of(
            "durationSeconds",
            15,
            "aspectRatio",
            "9:16",
            "firstFrameImageId",
            "library/frame.png"));
    assertThatThrownBy(() -> service.admission(id, queued))
        .isInstanceOf(IllegalStateException.class);
    queued.put(
        "settings",
        Map.of(
            "durationSeconds",
            6,
            "aspectRatio",
            "9:16",
            "firstFrameImageId",
            "library/other-frame.png"));
    assertThatThrownBy(() -> service.admission(id, queued))
        .isInstanceOf(IllegalStateException.class);
  }

  @Test
  void editorialCandidateCannotAuthorizeRenderAndUngroundedObservationIsUnknown() {
    var candidate =
        Map.<String, Object>of(
            "bindingHash",
            "b",
            "authorizationScope",
            "EDITORIAL_ASSESSMENT_ONLY",
            "family8",
            Map.of("renderAuthorization", Map.of("status", "AUTHORIZED")));
    assertThatThrownBy(() -> WorkflowService.requireAuthorized(candidate, "b"))
        .isInstanceOf(IllegalStateException.class);
    var item =
        Map.<String, Object>of(
            "state",
            "PRESENT",
            "confidence",
            "HIGH",
            "evidenceBasis",
            "HUMAN_REVIEWED_CLIP",
            "reference",
            "cover.jpg");
    assertThat(WorkflowService.checkedObservation(item, true, "clip.mp4"))
        .containsEntry("confidence", "UNKNOWN");
    var grounded = new java.util.LinkedHashMap<String, Object>(item);
    grounded.put("reference", "clip.mp4#t=0,2");
    assertThat(WorkflowService.checkedObservation(grounded, true, "clip.mp4"))
        .containsEntry("confidence", "HIGH");
    assertThat(WorkflowService.checkedObservation(grounded, false, "clip.mp4"))
        .containsEntry("confidence", "UNKNOWN");
  }

  @Test
  void essentialSignatureUsesSourceSupportedIntentAndStillsCannotAuthorizeMotion() {
    var review =
        Map.<String, Object>of(
            "intentRequirements",
            java.util.List.of(
                Map.of("level", "ESSENTIAL", "sourceQuote", "Reveal", "status", "SOURCE_SUPPORTED"),
                Map.of(
                    "level",
                    "POLISH",
                    "sourceQuote",
                    "Smooth contact",
                    "status",
                    "SOURCE_SUPPORTED")));
    assertThat(WorkflowService.essentialSignature(review)).containsExactly("Reveal");
    var frame =
        Map.<String, Object>of(
            "evidenceBasis",
            "DENSE_LOCAL_FRAMES",
            "requiresMotion",
            false,
            "reference",
            "clip.mp4#t=0,0",
            "confidence",
            "MEDIUM");
    assertThat(WorkflowService.checkedObservation(frame, false, true, "clip.mp4"))
        .containsEntry("confidence", "MEDIUM");
    var motion = new java.util.LinkedHashMap<String, Object>(frame);
    motion.put("requiresMotion", true);
    assertThat(WorkflowService.checkedObservation(motion, false, true, "clip.mp4"))
        .containsEntry("confidence", "UNKNOWN");
  }
}
