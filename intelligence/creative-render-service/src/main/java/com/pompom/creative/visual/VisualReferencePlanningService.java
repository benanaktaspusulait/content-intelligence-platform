package com.pompom.creative.visual;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.openart.OpenArtAdapter;
import com.pompom.creative.openart.OpenArtCapabilities;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.CreditTrackingService;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Plans visual references from immutable render snapshots without invoking a provider. */
@Service
public class VisualReferencePlanningService {
  private final RenderJobRepository jobs;
  private final RenderAttemptRepository attempts;
  private final RenderAssetRepository assets;
  private final VisualReferencePlanRepository plans;
  private final VisualReferenceAssetRepository planAssets;
  private final OpenArtAdapter openArt;
  private final CreditTrackingService credits;
  private final ObjectMapper mapper;
  private final Path dataRoot;

  public VisualReferencePlanningService(
      RenderJobRepository jobs,
      RenderAttemptRepository attempts,
      RenderAssetRepository assets,
      VisualReferencePlanRepository plans,
      VisualReferenceAssetRepository planAssets,
      OpenArtAdapter openArt,
      CreditTrackingService credits,
      ObjectMapper mapper,
      @Value("${pompom.data.root:/tmp/pompom-data}") String dataRoot) {
    this.jobs = jobs;
    this.attempts = attempts;
    this.assets = assets;
    this.plans = plans;
    this.planAssets = planAssets;
    this.openArt = openArt;
    this.credits = credits;
    this.mapper = mapper;
    this.dataRoot = Path.of(dataRoot).toAbsolutePath().normalize();
  }

  @Transactional
  public Map<String, Object> inspect(UUID renderJobId) {
    RenderJob job = jobs.findById(renderJobId).orElseThrow(() -> new IllegalArgumentException("Render job not found"));
    List<RenderAsset> candidates = firstFrameCandidates(job);
    String status = firstFrameStatus(job, candidates);
    OpenArtCapabilities capabilities = openArt.capabilities();
    Map<String, Object> recommendation = new LinkedHashMap<>(recommendation(job, status, capabilities));
    if ("MISSING".equals(status)) recommendation.put("generationProposal", generationProposal(job));
    VisualReferencePlan plan = plans.findByRenderJobId(renderJobId).orElseGet(VisualReferencePlan::new);
    plan.setRenderJob(job);
    plan.setContentId(job.getContentId());
    plan.setPromptVersionId(job.getPromptVersionId());
    plan.setPromptSha256(job.getPromptSha256());
    plan.setProvider("OPENART_CLI");
    plan.setModel(job.getOpenartModel());
    plan.setFirstFrameStatus(status);
    plan.setStrategy(String.valueOf(recommendation.get("strategy")));
    plan.setValidationStatus(status.startsWith("AVAILABLE") ? "REVIEW_REQUIRED" : "UNKNOWN");
    plan.setRecommendationJson(json(recommendation));
    plan.setCapabilitiesJson(json(capabilitiesMap(capabilities)));
    plan.setCostEstimateJson(json(costMap()));
    plan = plans.save(plan);
    List<Map<String, Object>> referenceViews = new ArrayList<>();
    for (RenderAsset asset : candidates) referenceViews.add(assetView(asset, job));
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("planId", plan.getId());
    result.put("renderJobId", renderJobId);
    result.put("contentId", job.getContentId());
    result.put("promptVersionId", job.getPromptVersionId());
    result.put("promptSha256", job.getPromptSha256());
    result.put("promptReady", job.getPromptTextSnapshot() != null && !job.getPromptTextSnapshot().isBlank());
    result.put("firstFrameStatus", status);
    result.put("firstFrameCandidates", referenceViews);
    result.put("referenceBindings", planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId()).stream().map(this::bindingView).toList());
    result.put("recommendation", recommendation);
    result.put("capabilities", capabilitiesMap(capabilities));
    result.put("modelCapabilities", modelCapabilities(job.getOpenartModel()));
    result.put("cost", costMap());
    result.put("generationProposal", status.equals("MISSING") ? recommendation.get("generationProposal") : null);
    result.put("paidCallPerformed", false);
    return result;
  }

  public Map<String, Object> prepareFirstFrameProposal(UUID planId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    RenderJob job = plan.getRenderJob();
    if (job.getPromptTextSnapshot() == null || job.getPromptTextSnapshot().isBlank()) throw new IllegalStateException("Complete and save the production prompt before preparing visual references");
    return Map.of("planId", planId, "role", "FIRST_FRAME", "sourcePromptVersionId", job.getPromptVersionId(), "sourcePromptSha256", job.getPromptSha256(), "provider", "OPENART_CLI", "model", job.getOpenartModel(), "request", generationProposal(job), "authorizationRequired", true, "paidCallPerformed", false);
  }

  @Transactional
  public Map<String, Object> validate(UUID planId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    List<VisualReferenceAsset> bindings = planAssets.findByPlanIdOrderByCreatedAtAsc(planId);
    List<Map<String, Object>> evidence = new ArrayList<>();
    for (VisualReferenceAsset binding : bindings) {
      boolean hashPresent = binding.getSha256() != null && !binding.getSha256().isBlank();
      boolean promptMatches = plan.getPromptSha256().equals(binding.getPromptSha256());
      evidence.add(Map.of("assetId", binding.getId(), "role", binding.getRole(), "metadataVerified", hashPresent, "promptVersionMatches", promptMatches, "identity", "UNKNOWN", "promptCompatibility", "UNKNOWN", "reason", "Semantic image evidence is not available from metadata alone."));
    }
    String status = bindings.isEmpty() ? "UNKNOWN" : "REVIEW_REQUIRED";
    plan.setValidationStatus(status);
    plans.save(plan);
    return Map.of("planId", planId, "status", status, "metadataVerified", !bindings.isEmpty(), "identity", "UNKNOWN", "promptCompatibility", "UNKNOWN", "crossReferenceConsistency", bindings.size() < 2 ? "NOT_APPLICABLE" : "UNKNOWN", "evidence", evidence, "serviceFailure", false);
  }

  @Transactional
  public Map<String, Object> uploadFirstFrame(UUID planId, org.springframework.web.multipart.MultipartFile file) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    if (file == null || file.isEmpty()) throw new IllegalArgumentException("An image file is required");
    if (file.getSize() > 20_000_000L) throw new IllegalArgumentException("Image exceeds the 20 MB limit");
    String contentType = file.getContentType() == null ? "" : file.getContentType().toLowerCase(java.util.Locale.ROOT);
    if (!contentType.startsWith("image/")) throw new IllegalArgumentException("Only image uploads are supported");
    try {
      java.awt.image.BufferedImage decoded = javax.imageio.ImageIO.read(file.getInputStream());
      if (decoded == null) throw new IllegalArgumentException("The uploaded file is not a decodable image");
      if (decoded.getWidth() < 1 || decoded.getHeight() < 1 || decoded.getWidth() > 8192 || decoded.getHeight() > 8192) throw new IllegalArgumentException("Image dimensions are outside the supported range");
      byte[] bytes = file.getBytes();
      String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
      Path directory = dataRoot.resolve("content").resolve(String.valueOf(plan.getContentId())).resolve("visual-references").normalize();
      if (!directory.startsWith(dataRoot)) throw new IllegalStateException("Unsafe visual reference storage path");
      Files.createDirectories(directory);
      Path target = directory.resolve(sha + "." + extension(contentType)).normalize();
      if (!target.startsWith(directory)) throw new IllegalStateException("Unsafe uploaded filename");
      if (!Files.exists(target)) Files.write(target, bytes);
      VisualReferenceAsset binding = VisualReferenceAsset.builder().plan(plan).role("FIRST_FRAME").sourceKind("IMPORTED").relativePath(dataRoot.relativize(target).toString()).sha256(sha).promptSha256(plan.getPromptSha256()).validationStatus("METADATA_VERIFIED").validationEvidenceJson(json(Map.of("contentType", contentType, "width", decoded.getWidth(), "height", decoded.getHeight(), "semanticStatus", "UNKNOWN"))).accepted(false).build();
      planAssets.save(binding);
      return Map.of("assetId", binding.getId(), "role", "FIRST_FRAME", "sourceKind", "IMPORTED", "relativePath", binding.getRelativePath(), "sha256", sha, "width", decoded.getWidth(), "height", decoded.getHeight(), "accepted", false, "semanticStatus", "UNKNOWN");
    } catch (IOException | NoSuchAlgorithmException e) {
      throw new IllegalStateException("Could not persist uploaded image", e);
    }
  }

  public void validateForRender(UUID planId, Long contentId, Long promptVersionId, String firstFramePath) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalStateException("Visual reference plan not found; render admission is closed"));
    if (!plan.getContentId().equals(contentId) || !plan.getPromptVersionId().equals(promptVersionId)) throw new IllegalStateException("Visual reference plan is bound to a different prompt version");
    List<VisualReferenceAsset> accepted = planAssets.findByPlanIdOrderByCreatedAtAsc(planId).stream().filter(a -> a.isAccepted() && "FIRST_FRAME".equals(a.getRole())).toList();
    if (accepted.isEmpty()) throw new IllegalStateException("An accepted FIRST_FRAME visual reference is required before video admission");
    if (firstFramePath == null || firstFramePath.isBlank() || accepted.stream().noneMatch(a -> samePath(firstFramePath, a.getRelativePath()))) throw new IllegalStateException("Queued first-frame binding does not match the accepted visual reference");
    if ("ADDITIONAL_IMAGE_NOT_SUPPORTED".equals(readJsonValue(plan.getRecommendationJson(), "criticalScene"))) throw new IllegalStateException("Selected critical-scene reference is unsupported by the active provider");
  }

  private String extension(String contentType) { return switch (contentType) { case "image/jpeg" -> "jpg"; case "image/webp" -> "webp"; case "image/gif" -> "gif"; default -> "png"; }; }
  private boolean samePath(String left, String right) { if (left == null || right == null) return false; String a = left.replace('\\', '/'); String b = right.replace('\\', '/'); if (a.startsWith("/data/")) a = a.substring(6); if (b.startsWith("/data/")) b = b.substring(6); return a.equals(b) || a.equals("data/" + b) || b.equals("data/" + a); }
  private String readJsonValue(String json, String field) { try { var node = mapper.readTree(json == null ? "{}" : json).get(field); return node == null ? "" : node.asText(); } catch (JsonProcessingException ignored) { return ""; } }

  @Transactional
  public Map<String, Object> acceptFirstFrame(UUID planId, UUID renderAssetId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    RenderAsset asset = assets.findById(renderAssetId).orElseThrow(() -> new IllegalArgumentException("Render asset not found"));
    if (asset.getAssetType() != RenderAsset.AssetType.FIRST_FRAME) throw new IllegalArgumentException("Only a FIRST_FRAME asset can be accepted");
    if (!plan.getRenderJob().getPromptSha256().equals(asset.getPromptHash())) throw new IllegalStateException("First frame belongs to a different prompt version");
    if (!Boolean.TRUE.equals(asset.getMediaVerified()) || Boolean.TRUE.equals(asset.getQuarantined()) || asset.getSha256() == null) throw new IllegalStateException("First frame needs technical validation before acceptance");
    VisualReferenceAsset binding = VisualReferenceAsset.builder().plan(plan).role("FIRST_FRAME").sourceKind("EXISTING").renderAssetId(asset.getId()).relativePath(asset.getRelativePath()).sha256(asset.getSha256()).promptSha256(asset.getPromptHash()).validationStatus("METADATA_VERIFIED").validationEvidenceJson(json(Map.of("mediaVerified", true, "semanticStatus", "UNKNOWN"))).accepted(true).build();
    planAssets.save(binding);
    plan.setFirstFrameStatus("AVAILABLE_REVIEW_REQUIRED");
    plan.setValidationStatus("REVIEW_REQUIRED");
    plans.save(plan);
    return Map.of("planId", planId, "assetId", renderAssetId, "role", "FIRST_FRAME", "accepted", true, "semanticStatus", "UNKNOWN");
  }

  @Transactional
  public Map<String, Object> acceptImportedFirstFrame(UUID planId, UUID referenceAssetId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    VisualReferenceAsset binding = planAssets.findById(referenceAssetId).orElseThrow(() -> new IllegalArgumentException("Visual reference asset not found"));
    if (!planId.equals(binding.getPlan().getId()) || !"FIRST_FRAME".equals(binding.getRole())) throw new IllegalArgumentException("Reference asset is not a first-frame candidate for this plan");
    if (!plan.getPromptSha256().equals(binding.getPromptSha256())) throw new IllegalStateException("Uploaded first frame belongs to a different prompt version");
    if (!"METADATA_VERIFIED".equals(binding.getValidationStatus())) throw new IllegalStateException("Uploaded first frame needs technical validation before acceptance");
    binding.setAccepted(true);
    planAssets.save(binding);
    plan.setFirstFrameStatus("AVAILABLE_REVIEW_REQUIRED");
    plan.setValidationStatus("REVIEW_REQUIRED");
    plans.save(plan);
    return Map.of("planId", planId, "assetId", referenceAssetId, "role", "FIRST_FRAME", "accepted", true, "semanticStatus", "UNKNOWN");
  }

  private List<RenderAsset> firstFrameCandidates(RenderJob job) {
    List<RenderAsset> result = new ArrayList<>();
    assets.findByRenderJobId(job.getId()).stream().filter(a -> a.getAssetType() == RenderAsset.AssetType.FIRST_FRAME).forEach(result::add);
    attempts.findByRenderJobIdOrderByAttemptNumberAsc(job.getId()).stream().map(a -> a.getFirstFrameAssetId()).filter(java.util.Objects::nonNull).flatMap(id -> assets.findById(id).stream()).filter(a -> !result.contains(a)).forEach(result::add);
    return result;
  }

  private String firstFrameStatus(RenderJob job, List<RenderAsset> candidates) {
    if (job.getPromptTextSnapshot() == null || job.getPromptTextSnapshot().isBlank()) return "UNKNOWN";
    if (candidates.isEmpty()) return "MISSING";
    if (candidates.stream().anyMatch(a -> !job.getPromptSha256().equals(a.getPromptHash()))) return "STALE";
    if (candidates.stream().anyMatch(a -> Boolean.TRUE.equals(a.getMediaVerified()) && !Boolean.TRUE.equals(a.getQuarantined()) && a.getSha256() != null && fileExists(a))) return "AVAILABLE_REVIEW_REQUIRED";
    return "AVAILABLE_REVIEW_REQUIRED";
  }

  private boolean fileExists(RenderAsset asset) {
    if (asset.getRelativePath() == null) return false;
    Path path = Path.of(asset.getRelativePath());
    if (!path.isAbsolute()) path = dataRoot.resolve(path);
    return Files.isRegularFile(path.normalize());
  }

  private Map<String, Object> recommendation(RenderJob job, String status, OpenArtCapabilities capabilities) {
    String strategy = "FIRST_FRAME_ONLY";
    String action = switch (status) { case "MISSING" -> "PREPARE_FIRST_FRAME"; case "STALE" -> "REVALIDATE_FIRST_FRAME"; case "AVAILABLE_REVIEW_REQUIRED" -> "REVIEW_EXISTING_FIRST_FRAME"; default -> "COMPLETE_PROMPT"; };
    String constraints = job.getCompiledGenerationConstraints() == null ? "" : job.getCompiledGenerationConstraints().toLowerCase(java.util.Locale.ROOT);
    boolean difficultState = java.util.regex.Pattern.compile("transform|reveal|scale|spatial|contact|continuity|state change").matcher(constraints).find();
    String criticalScene = difficultState ? (capabilities.videoMultipleElementReferences() == OpenArtCapabilities.Support.SUPPORTED ? "FIRST_FRAME_PLUS_CRITICAL_REFERENCE_RECOMMENDED" : "ADDITIONAL_IMAGE_NOT_SUPPORTED") : "INSUFFICIENT_EVIDENCE";
    String reason = difficultState ? (criticalScene.equals("ADDITIONAL_IMAGE_NOT_SUPPORTED") ? "Structured constraints suggest a difficult visual state, but the active OpenArt video contract supports only one start image." : "Structured constraints identify a potentially difficult visual state; review one optional additional reference.") : "Use the fewest references necessary; no critical-scene image is recommended without structured beat evidence.";
    return Map.of("strategy", strategy, "action", action, "criticalScene", criticalScene, "reason", reason, "additionalReferenceSupport", capabilities.videoMultipleElementReferences().name());
  }

  private Map<String, Object> generationProposal(RenderJob job) {
    return Map.of("promptText", "Opening still for the accepted production prompt. Show the exact visible opening state, recognizable approved characters, required object and spatial relationships, consistent environment, child-appropriate presentation, and clear framing. Do not depict later transformations or the full video timeline.\n\nACCEPTED PRODUCTION PROMPT:\n" + job.getPromptTextSnapshot(), "model", job.getOpenartModel(), "referenceRoles", List.of("CHARACTER_REFERENCE", "SCENE_REFERENCE"), "aspectRatio", "FROM_APPROVED_RENDER_SETTINGS", "dimensions", "FROM_PROVIDER_CAPABILITY", "costStatus", "ESTIMATE_ONLY");
  }

  private Map<String, Object> modelCapabilities(String model) {
    String normalized = model == null ? "" : model.toLowerCase(java.util.Locale.ROOT);
    String start = normalized.contains("seedance-2") ? "SUPPORTED" : "UNVERIFIED";
    String multiple = normalized.contains("seedance-2") ? "UNSUPPORTED" : "UNVERIFIED";
    String end = normalized.contains("seedance-2.5") ? "UNVERIFIED" : "UNSUPPORTED";
    return Map.of("model", model == null ? "" : model, "startFrame", start, "endFrame", end, "multipleVideoReferences", multiple, "intermediateKeyframe", "UNSUPPORTED", "segmentContinuation", "UNVERIFIED", "verificationSource", "OpenArt CLI 0.1.1 local capability snapshot");
  }

  private Map<String, Object> capabilitiesMap(OpenArtCapabilities c) { return Map.of("imageMultipleReferences", c.imageMultipleReferences().name(), "videoSingleStartFrame", c.videoSingleStartFrame().name(), "videoMultipleElementReferences", c.videoMultipleElementReferences().name(), "workspaceAssetDiscovery", c.workspaceAssetDiscovery().name()); }
  private Map<String, Object> costMap() { BigDecimal frame = credits.getEstimatedCost(RenderJob.JobType.FIRST_FRAME); return Map.of("imageGenerationCredits", frame == null ? "UNKNOWN" : frame, "visionValidation", "UNKNOWN", "paidCallPerformed", false); }
  private Map<String, Object> assetView(RenderAsset a, RenderJob job) { return Map.of("assetId", a.getId(), "role", "FIRST_FRAME", "source", a.getSource() == null ? "UNKNOWN" : a.getSource(), "relativePath", a.getRelativePath(), "sha256", a.getSha256() == null ? "" : a.getSha256(), "promptSha256", a.getPromptHash() == null ? "" : a.getPromptHash(), "promptVersionMatches", job.getPromptSha256().equals(a.getPromptHash()), "mediaVerified", Boolean.TRUE.equals(a.getMediaVerified()), "semanticStatus", "UNKNOWN"); }
  private Map<String, Object> bindingView(VisualReferenceAsset asset) { return Map.of("assetId", asset.getId(), "role", asset.getRole(), "sourceKind", asset.getSourceKind(), "relativePath", asset.getRelativePath() == null ? "" : asset.getRelativePath(), "sha256", asset.getSha256() == null ? "" : asset.getSha256(), "validationStatus", asset.getValidationStatus(), "accepted", asset.isAccepted()); }
  private String json(Object value) { try { return mapper.writeValueAsString(value); } catch (JsonProcessingException e) { throw new IllegalStateException("Could not serialize visual reference plan", e); } }
}
