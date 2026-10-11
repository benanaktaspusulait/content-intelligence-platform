package com.pompom.creative.visual;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtCapabilities;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.CreditTrackingService;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class VisualReferencePlanningServiceTest {
  private RenderJobRepository jobs;
  private IntelligenceContentClient content;
  private RenderAssetRepository assets;
  private VisualReferencePlanRepository plans;
  private VisualReferenceAssetRepository planAssets;
  private OpenArtAdapter openArt;
  private CreditTrackingService credits;
  private VisualReferencePlanningService service;

  @BeforeEach
  void setUp() {
    jobs = mock(RenderJobRepository.class);
    content = mock(IntelligenceContentClient.class);
    assets = mock(RenderAssetRepository.class);
    plans = mock(VisualReferencePlanRepository.class);
    planAssets = mock(VisualReferenceAssetRepository.class);
    openArt = mock(OpenArtAdapter.class);
    credits = mock(CreditTrackingService.class);
    when(content.fetch(8L, 8L)).thenReturn(new ContentPromptSnapshot(
        "v1", 8L, "Mimi", "REEL", "DRAFT_BUILT", 8L, 1, "Mimi opens a cabinet.", "{}", "a".repeat(64)));
    when(openArt.capabilities()).thenReturn(OpenArtCapabilities.cliV011());
    when(credits.getEstimatedCost(RenderJob.JobType.FIRST_FRAME)).thenReturn(new BigDecimal("10"));
    when(plans.findFirstByContentIdAndPromptVersionIdAndRenderJobIsNullOrderByUpdatedAtDesc(8L, 8L)).thenReturn(Optional.empty());
    when(plans.save(any(VisualReferencePlan.class))).thenAnswer(call -> {
      var plan = (VisualReferencePlan) call.getArgument(0);
      if (plan.getId() == null) plan.setId(java.util.UUID.randomUUID());
      return plan;
    });
    when(assets.findByContentIdOrderByCreatedAtDesc(8L)).thenReturn(List.of());
    when(planAssets.findByPlanIdOrderByCreatedAtAsc(any())).thenReturn(List.of());
    service = new VisualReferencePlanningService(jobs, content, mock(RenderAttemptRepository.class), assets,
        plans, planAssets, openArt, credits, new ObjectMapper(), "/tmp/pompom-data");
  }

  @Test
  void inspectsAndPersistsProviderFreeVisualPlanBoundToImmutablePromptBeforeRenderJob() {
    var result = service.inspectPrompt(8L, 8L, "seedance-2-mini");

    assertThat(result).containsEntry("contentId", 8L).containsEntry("promptVersionId", 8L)
        .containsEntry("promptVersionNumber", 1).containsEntry("promptSha256", "a".repeat(64))
        .containsEntry("promptReady", true).containsEntry("paidCallPerformed", false);
    assertThat(result.get("planId")).isNotNull();
    var saved = org.mockito.ArgumentCaptor.forClass(VisualReferencePlan.class);
    verify(plans).save(saved.capture());
    assertThat(saved.getValue().getRenderJob()).isNull();
    assertThat(saved.getValue().getContentId()).isEqualTo(8L);
    assertThat(saved.getValue().getPromptVersionId()).isEqualTo(8L);
    assertThat(saved.getValue().getPromptSha256()).isEqualTo("a".repeat(64));
    verifyNoInteractions(jobs);
  }

  @Test
  void neverTreatsExistingAssetsAsSemanticallyVerifiedEvidence() {
    var result = service.inspectPrompt(8L, 8L, "seedance-2-mini");
    assertThat(result.get("firstFrameStatus")).isEqualTo("MISSING");
    assertThat(result.get("paidCallPerformed")).isEqualTo(false);
  }

  @Test
  void refreshIsReadOnlyAndRetainsRealVersionNumberWithoutCreatingPlan() {
    var result = service.readPrompt(8L, 8L, "seedance-2-mini");
    assertThat(result).containsEntry("promptVersionNumber", 1).containsEntry("promptVersionId", 8L);
    assertThat(result.get("planId")).isNull();
    verify(plans, never()).save(any());
    verifyNoInteractions(jobs, planAssets);
    verify(openArt, only()).capabilities();
  }

  @Test
  void readOnlyRestoreHidesStaleBindingsWithoutModifyingPersistedEvidence() {
    var plan = VisualReferencePlan.builder().id(java.util.UUID.randomUUID()).contentId(8L)
        .promptVersionId(8L).promptSha256("b".repeat(64)).model("seedance-2-mini").build();
    when(plans.findFirstByContentIdAndPromptVersionIdAndRenderJobIsNullOrderByUpdatedAtDesc(8L, 8L)).thenReturn(Optional.of(plan));
    var result = service.readPrompt(8L, 8L, "seedance-2-mini");
    assertThat((List<?>)result.get("referenceBindings")).isEmpty();
    assertThat(plan.getPromptSha256()).isEqualTo("b".repeat(64));
    verify(plans, never()).save(any());
  }

  @Test
  void uploadNeverAcceptsOrCallsProvider(@org.junit.jupiter.api.io.TempDir java.nio.file.Path directory) throws Exception {
    service = new VisualReferencePlanningService(jobs, content, mock(RenderAttemptRepository.class), assets,
        plans, planAssets, openArt, credits, new ObjectMapper(), directory.toString());
    var plan = VisualReferencePlan.builder().id(java.util.UUID.randomUUID()).contentId(8L)
        .promptVersionId(8L).promptSha256("a".repeat(64)).model("seedance-2-mini").build();
    when(plans.findById(plan.getId())).thenReturn(Optional.of(plan));
    when(planAssets.save(any())).thenAnswer(call -> { var binding = (VisualReferenceAsset)call.getArgument(0); binding.setId(java.util.UUID.randomUUID()); return binding; });
    var out = new java.io.ByteArrayOutputStream();
    javax.imageio.ImageIO.write(new java.awt.image.BufferedImage(90,160,java.awt.image.BufferedImage.TYPE_INT_RGB), "png", out);
    var result = service.uploadFirstFrame(plan.getId(), new org.springframework.mock.web.MockMultipartFile("file", "frame.png", "image/png", out.toByteArray()));
    assertThat(result).containsEntry("accepted", false).containsEntry("semanticStatus", "UNKNOWN");
    verifyNoInteractions(openArt, credits, jobs);
  }

  @Test
  void acceptanceRejectsWrongRatioAndBindsValidImageToExactContract(@org.junit.jupiter.api.io.TempDir java.nio.file.Path directory) throws Exception {
    service = new VisualReferencePlanningService(jobs, content, mock(RenderAttemptRepository.class), assets,
        plans, planAssets, openArt, credits, new ObjectMapper(), directory.toString());
    var plan = VisualReferencePlan.builder().id(java.util.UUID.randomUUID()).contentId(8L)
        .promptVersionId(8L).promptSha256("a".repeat(64)).model("seedance-2-mini").build();
    var path = directory.resolve("image.png");
    javax.imageio.ImageIO.write(new java.awt.image.BufferedImage(90,160,java.awt.image.BufferedImage.TYPE_INT_RGB), "png", path.toFile());
    String checksum = java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(java.nio.file.Files.readAllBytes(path)));
    var binding = VisualReferenceAsset.builder().id(java.util.UUID.randomUUID()).plan(plan).role("FIRST_FRAME")
        .relativePath("image.png").sha256(checksum).promptSha256("a".repeat(64)).validationStatus("METADATA_VERIFIED").accepted(false).build();
    when(plans.findById(plan.getId())).thenReturn(Optional.of(plan));
    when(planAssets.findById(binding.getId())).thenReturn(Optional.of(binding));
    when(planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId())).thenReturn(List.of(binding));
    org.assertj.core.api.Assertions.assertThatThrownBy(() -> service.acceptImportedFirstFrame(plan.getId(), binding.getId(), java.util.Map.of("aspectRatio", "1:1", "model", "seedance-2-mini"))).hasMessageContaining("aspect ratio");
    assertThat(binding.isAccepted()).isFalse();
    service.acceptImportedFirstFrame(plan.getId(), binding.getId(), java.util.Map.of("aspectRatio", "9:16", "model", "seedance-2-mini", "mode", "IMAGE_TO_VIDEO", "characterReferenceAssetId", "mimi-asset"));
    assertThat(binding.isAccepted()).isTrue();
    var evidence = new ObjectMapper().readTree(binding.getValidationEvidenceJson());
    assertThat(evidence.path("promptVersionId").asLong()).isEqualTo(8);
    assertThat(evidence.path("contentId").asLong()).isEqualTo(8);
    assertThat(evidence.path("checksum").asText()).isEqualTo(checksum);
    assertThat(evidence.path("semanticStatus").asText()).isEqualTo("UNKNOWN");
    org.assertj.core.api.Assertions.assertThatThrownBy(() -> service.validateForRender(plan.getId(), 8L, 8L, "image.png", "different-model", java.util.Map.of("aspectRatio", "9:16"))).hasMessageContaining("generator");
    verifyNoInteractions(openArt, credits, jobs);
  }

  @Test
  void acceptanceRejectsOtherPromptAndPlanBeforeMutating() {
    var plan = VisualReferencePlan.builder().id(java.util.UUID.randomUUID()).contentId(8L).promptVersionId(8L).promptSha256("a".repeat(64)).build();
    var other = VisualReferencePlan.builder().id(java.util.UUID.randomUUID()).build();
    var binding = VisualReferenceAsset.builder().id(java.util.UUID.randomUUID()).plan(other).role("FIRST_FRAME").accepted(false).build();
    when(plans.findById(plan.getId())).thenReturn(Optional.of(plan));
    when(planAssets.findById(binding.getId())).thenReturn(Optional.of(binding));
    org.assertj.core.api.Assertions.assertThatThrownBy(() -> service.acceptImportedFirstFrame(plan.getId(), binding.getId(), java.util.Map.of())).hasMessageContaining("not a first-frame candidate");
    verify(planAssets, never()).save(any());
  }
}
