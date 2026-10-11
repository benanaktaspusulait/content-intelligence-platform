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
import com.pompom.creative.intelligence.IntelligenceContentClient;
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
  private final IntelligenceContentClient content;
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
      IntelligenceContentClient content,
      RenderAttemptRepository attempts,
      RenderAssetRepository assets,
      VisualReferencePlanRepository plans,
      VisualReferenceAssetRepository planAssets,
      OpenArtAdapter openArt,
      CreditTrackingService credits,
      ObjectMapper mapper,
      @Value("${pompom.data.root:/tmp/pompom-data}") String dataRoot) {
    this.jobs = jobs;
    this.content = content;
    this.attempts = attempts;
    this.assets = assets;
    this.plans = plans;
    this.planAssets = planAssets;
    this.openArt = openArt;
    this.credits = credits;
    this.mapper = mapper;
    this.dataRoot = Path.of(dataRoot).toAbsolutePath().normalize();
  }

  /** Create or restore a prompt-bound visual preparation plan before any RenderJob exists. */
  @Transactional
  public Map<String, Object> inspectPrompt(Long contentId, Long promptVersionId, String requestedModel) {
    return promptView(contentId, promptVersionId, requestedModel, true);
  }

  /** Page restoration must not create or update planning records. */
  @Transactional(readOnly = true)
  public Map<String, Object> readPrompt(Long contentId, Long promptVersionId, String requestedModel) {
    return promptView(contentId, promptVersionId, requestedModel, false);
  }

  private Map<String, Object> promptView(Long contentId, Long promptVersionId, String requestedModel, boolean persist) {
    var snapshot = content.fetch(contentId, promptVersionId);
    if (snapshot.contentId() != contentId || snapshot.promptVersionId() != promptVersionId) throw new IllegalStateException("Immutable prompt snapshot belongs to a different project or version");
    if (snapshot.promptText() == null || snapshot.promptText().isBlank()
        || snapshot.promptSha256() == null || !snapshot.promptSha256().matches("[0-9a-f]{64}"))
      throw new IllegalStateException("A complete immutable prompt snapshot is required for visual preparation");
    String model = requestedModel == null || requestedModel.isBlank() ? "" : requestedModel.trim();
    VisualReferencePlan plan = plans.findFirstByContentIdAndPromptVersionIdAndRenderJobIsNullOrderByUpdatedAtDesc(contentId, promptVersionId)
        .orElseGet(VisualReferencePlan::new);
    boolean stale = plan.getPromptSha256() != null && !plan.getPromptSha256().equals(snapshot.promptSha256());
    if (persist && stale) {
      for (VisualReferenceAsset binding : planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId())) {
        if (binding.isAccepted()) binding.setAccepted(false);
        binding.setValidationStatus("STALE");
      }
    }
    String status = preRenderFirstFrameStatus(contentId, snapshot.promptSha256());
    var openArtCapabilities = openArt.capabilities();
    Map<String, Object> recommendation = new LinkedHashMap<>();
    recommendation.put("strategy", "FIRST_FRAME_ONLY");
    recommendation.put("action", "MISSING".equals(status) ? "UPLOAD_OR_SELECT_FIRST_FRAME" : "REVIEW_EXISTING_FIRST_FRAME");
    recommendation.put("criticalScene", "INSUFFICIENT_EVIDENCE");
    recommendation.put("reason", "Visual planning is provider-free; first-frame identity and semantic evidence remain UNKNOWN until reviewed.");
    recommendation.put("additionalReferenceSupport", openArtCapabilities.videoMultipleElementReferences().name());
    String selectedModel = model.isBlank() ? plan.getModel() : model;
    if (selectedModel == null || selectedModel.isBlank()) selectedModel = "UNKNOWN";
    if (persist) {
    plan.setRenderJob(null);
    plan.setContentId(contentId);
    plan.setPromptVersionId(promptVersionId);
    plan.setPromptSha256(snapshot.promptSha256());
    plan.setProvider("OPENART_CLI");
    plan.setModel(selectedModel);
    plan.setFirstFrameStatus(status);
    plan.setStrategy("FIRST_FRAME_ONLY");
    plan.setValidationStatus("MISSING".equals(status) ? "UNKNOWN" : "REVIEW_REQUIRED");
    plan.setRecommendationJson(json(recommendation));
    plan.setCapabilitiesJson(json(capabilitiesMap(openArtCapabilities)));
    plan.setCostEstimateJson(json(costMap()));
    plan = plans.save(plan);
    }
    List<Map<String, Object>> candidates = assets.findByContentIdOrderByCreatedAtDesc(contentId).stream()
        .filter(a -> a.getAssetType() == RenderAsset.AssetType.FIRST_FRAME)
        .map(a -> assetView(a, snapshot.promptSha256())).toList();
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("planId", plan.getId());
    result.put("contentId", contentId);
    result.put("promptVersionId", promptVersionId);
    result.put("promptVersionNumber", snapshot.promptVersionNumber());
    result.put("promptSha256", snapshot.promptSha256());
    result.put("promptReady", true);
    result.put("firstFrameStatus", status);
    result.put("firstFrameCandidates", candidates);
    result.put("referenceBindings", plan.getId() == null || stale ? List.of() : planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId()).stream().map(this::bindingView).toList());
    result.put("recommendation", recommendation);
    result.put("capabilities", capabilitiesMap(openArtCapabilities));
    result.put("modelCapabilities", modelCapabilities(selectedModel));
    result.put("cost", costMap());
    result.put("generationProposal", null);
    result.put("paidCallPerformed", false);
    return result;
  }

  private String preRenderFirstFrameStatus(Long contentId, String promptHash) {
    var candidates = assets.findByContentIdOrderByCreatedAtDesc(contentId).stream()
        .filter(a -> a.getAssetType() == RenderAsset.AssetType.FIRST_FRAME).toList();
    if (candidates.isEmpty()) return "MISSING";
    boolean matching = candidates.stream().anyMatch(a -> promptHash.equals(a.getPromptHash()));
    if (!matching && candidates.stream().anyMatch(a -> !promptHash.equals(a.getPromptHash()))) return "MISMATCH_CONFIRMED";
    return "AVAILABLE_REVIEW_REQUIRED";
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
    // A plan is prompt-bound. If a prompt revision is inspected again, accepted
    // bindings from the previous revision must never silently carry forward.
    boolean promptChanged = plan.getPromptSha256() != null && !plan.getPromptSha256().equals(job.getPromptSha256());
    if (promptChanged && plan.getId() != null) {
      for (VisualReferenceAsset binding : planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId())) {
        if (binding.isAccepted()) binding.setAccepted(false);
        binding.setValidationStatus("STALE");
        binding.setValidationEvidenceJson(json(Map.of("reason", "Prompt revision changed", "previousPromptSha256", String.valueOf(binding.getPromptSha256()), "currentPromptSha256", String.valueOf(job.getPromptSha256()))));
        planAssets.save(binding);
      }
    }
    plan.setRenderJob(job);
    plan.setContentId(job.getContentId());
    plan.setPromptVersionId(job.getPromptVersionId());
    plan.setPromptSha256(job.getPromptSha256());
    plan.setProvider("OPENART_CLI");
    plan.setModel(job.getOpenartModel());
    plan.setFirstFrameStatus(status);
    plan.setStrategy(String.valueOf(recommendation.get("strategy")));
    plan.setValidationStatus(status.equals("MISMATCH_CONFIRMED") ? "MISMATCH_CONFIRMED" : status.startsWith("AVAILABLE") ? "REVIEW_REQUIRED" : "UNKNOWN");
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
    var snapshot = job == null ? content.fetch(plan.getContentId(), plan.getPromptVersionId()) : null;
    String prompt = job == null ? snapshot.promptText() : job.getPromptTextSnapshot();
    if (prompt == null || prompt.isBlank()) throw new IllegalStateException("Complete and save the production prompt before preparing visual references");
    return Map.of("planId", planId, "role", "FIRST_FRAME", "sourcePromptVersionId", plan.getPromptVersionId(), "sourcePromptSha256", plan.getPromptSha256(), "provider", "OPENART_CLI", "model", plan.getModel(), "request", Map.of("promptText", "Opening still for the accepted production prompt. Show only the exact opening state; preserve approved identity and object relationships.\n\nACCEPTED PRODUCTION PROMPT:\n" + prompt, "model", plan.getModel(), "referenceRoles", List.of("CHARACTER_REFERENCE"), "aspectRatio", "FROM_APPROVED_RENDER_SETTINGS", "dimensions", "FROM_PROVIDER_CAPABILITY", "costStatus", "ESTIMATE_ONLY"), "authorizationRequired", true, "paidCallPerformed", false);
  }

  /** Returns a bounded, review-only critical-scene request; it never calls an image provider. */
  public Map<String, Object> prepareCriticalSceneProposal(UUID planId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    RenderJob job = plan.getRenderJob();
    Map<String, Object> recommendation = readObject(plan.getRecommendationJson());
    String criticalScene = String.valueOf(recommendation.getOrDefault("criticalScene", "INSUFFICIENT_EVIDENCE"));
    if (!"FIRST_FRAME_PLUS_CRITICAL_REFERENCE_RECOMMENDED".equals(criticalScene)) {
      throw new IllegalStateException("A critical-scene reference is not supported by the current evidence and provider capability");
    }
    return Map.of("planId", planId, "role", "CRITICAL_SCENE", "beatId", recommendation.getOrDefault("criticalBeatId", "UNSPECIFIED_BEAT"), "narrativePosition", recommendation.getOrDefault("narrativePosition", "UNSPECIFIED"), "intendedState", recommendation.getOrDefault("intendedState", "UNSPECIFIED"), "sharedRequirements", List.of("approved character identity", "costume continuity", "environment continuity", "object count and state", "prompt lineage"), "promptText", "Critical-scene reference for the approved production prompt. Preserve approved identity, costume, environment, object count, and spatial relationships; depict only the intended state change at the selected beat. This is an ordinary reference image for review, not a time-controlled keyframe.\n\nAPPROVED PROMPT:\n" + job.getPromptTextSnapshot(), "authorizationRequired", true, "paidCallPerformed", false);
  }

  @Transactional
  public Map<String, Object> validate(UUID planId) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    List<VisualReferenceAsset> bindings = planAssets.findByPlanIdOrderByCreatedAtAsc(planId);
    List<Map<String, Object>> evidence = new ArrayList<>();
    boolean mismatch = false;
    boolean insufficient = false;
    for (VisualReferenceAsset binding : bindings) {
      boolean hashPresent = binding.getSha256() != null && !binding.getSha256().isBlank();
      boolean promptMatches = plan.getPromptSha256() != null && plan.getPromptSha256().equals(binding.getPromptSha256());
      boolean pathPresent = binding.getRelativePath() != null && !binding.getRelativePath().isBlank();
      String classification;
      String reason;
      if (!promptMatches) {
        mismatch = true;
        classification = "MATERIAL_MISMATCH";
        reason = "Reference prompt lineage does not match the approved prompt revision.";
      } else if (!hashPresent || !pathPresent) {
        insufficient = true;
        classification = "INSUFFICIENT_EVIDENCE";
        reason = "Technical metadata is incomplete; semantic compatibility cannot be established.";
      } else {
        insufficient = true;
        classification = "INSUFFICIENT_EVIDENCE";
        reason = "Technical metadata is valid, but semantic image evidence is not available from metadata alone.";
      }
      evidence.add(Map.of("assetId", binding.getId(), "role", binding.getRole(), "metadataVerified", hashPresent && pathPresent, "promptVersionMatches", promptMatches, "identity", classification, "promptCompatibility", classification, "classification", classification, "minimumCorrection", mismatch ? "Re-select or upload a reference generated for the current prompt revision." : "Run an approved semantic/vision check or keep the asset in review.", "reason", reason));
    }
    String status = bindings.isEmpty() ? "UNKNOWN" : mismatch ? "MISMATCH_CONFIRMED" : insufficient ? "INSUFFICIENT_EVIDENCE" : "REVIEW_REQUIRED";
    VisualReferenceEvidenceClassifier.Result crossReference = VisualReferenceEvidenceClassifier.classify(bindings, plan.getPromptSha256());
    plan.setValidationStatus(status);
    plans.save(plan);
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("planId", planId); result.put("status", status); result.put("metadataVerified", !bindings.isEmpty());
    result.put("identity", mismatch ? "MATERIAL_MISMATCH" : "UNKNOWN"); result.put("promptCompatibility", mismatch ? "MATERIAL_MISMATCH" : "UNKNOWN");
    result.put("crossReferenceConsistency", crossReference.crossReferenceConsistency()); result.put("crossReferenceClassification", crossReference.classification()); result.put("crossReferenceReason", crossReference.reason());
    result.put("evidence", evidence); result.put("minimumCorrection", mismatch ? "Replace stale references and re-run validation." : "Obtain explicit semantic evidence before treating the reference as a match."); result.put("serviceFailure", false);
    return result;
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
    var snapshot = content.fetch(contentId, promptVersionId);
    if (!plan.getPromptSha256().equals(snapshot.promptSha256())) throw new IllegalStateException("Accepted visual plan prompt is stale");
    for (var binding : accepted) if (samePath(firstFramePath, binding.getRelativePath())) verifiedImagePath(binding.getRelativePath(), binding.getSha256());
    String startFrameSupport = String.valueOf(modelCapabilities(plan.getModel()).get("startFrame"));
    if (!"SUPPORTED".equals(startFrameSupport)) throw new IllegalStateException("The active OpenArt model has no verified start-frame contract; paid submission is blocked");
    if ("ADDITIONAL_IMAGE_NOT_SUPPORTED".equals(readJsonValue(plan.getRecommendationJson(), "criticalScene"))) throw new IllegalStateException("Selected critical-scene reference is unsupported by the active provider");
  }

  public void validateForRender(UUID planId, Long contentId, Long promptVersionId, String firstFramePath, String model, Map<String, Object> params) {
    var plan = plans.findById(planId).orElseThrow();
    if (!plan.getModel().equals(model)) throw new IllegalStateException("Accepted first frame generator is stale");
    validateForRender(planId, contentId, promptVersionId, firstFramePath);
    var binding = planAssets.findByPlanIdOrderByCreatedAtAsc(planId).stream()
        .filter(a -> a.isAccepted() && "FIRST_FRAME".equals(a.getRole()) && samePath(firstFramePath, a.getRelativePath())).findFirst().orElseThrow();
    String ratio = String.valueOf(params.getOrDefault("aspectRatio", ""));
    if (!ratio.equals(readJsonValue(binding.getValidationEvidenceJson(), "aspectRatio"))) throw new IllegalStateException("Accepted first frame aspect ratio is stale");
    for (String field : List.of("characterReferenceAssetId", "mode")) {
      if (!String.valueOf(params.get(field) == null ? "" : params.get(field)).equals(readJsonValue(binding.getValidationEvidenceJson(), field))) throw new IllegalStateException("Accepted first frame " + field + " is stale");
    }
  }

  private String extension(String contentType) { return switch (contentType) { case "image/jpeg" -> "jpg"; case "image/webp" -> "webp"; case "image/gif" -> "gif"; default -> "png"; }; }
  private boolean samePath(String left, String right) { if (left == null || right == null) return false; String a = left.replace('\\', '/'); String b = right.replace('\\', '/'); if (a.startsWith("/data/")) a = a.substring(6); if (b.startsWith("/data/")) b = b.substring(6); return a.equals(b) || a.equals("data/" + b) || b.equals("data/" + a); }
  private String readJsonValue(String json, String field) { try { var node = mapper.readTree(json == null ? "{}" : json).get(field); return node == null ? "" : node.asText(); } catch (JsonProcessingException ignored) { return ""; } }

  @Transactional
  public Map<String, Object> acceptFirstFrame(UUID planId, UUID renderAssetId) {
    return acceptFirstFrame(planId, renderAssetId, Map.of());
  }

  @Transactional
  public Map<String, Object> acceptFirstFrame(UUID planId, UUID renderAssetId, Map<String, Object> contract) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    RenderAsset asset = assets.findById(renderAssetId).orElseThrow(() -> new IllegalArgumentException("Render asset not found"));
    if (asset.getAssetType() != RenderAsset.AssetType.FIRST_FRAME) throw new IllegalArgumentException("Only a FIRST_FRAME asset can be accepted");
    if (!plan.getPromptSha256().equals(asset.getPromptHash()) || !plan.getContentId().equals(asset.getContentId())) throw new IllegalStateException("First frame belongs to a different content or prompt version");
    if (!Boolean.TRUE.equals(asset.getMediaVerified()) || Boolean.TRUE.equals(asset.getQuarantined()) || asset.getSha256() == null) throw new IllegalStateException("First frame needs technical validation before acceptance");
    var evidence = acceptanceEvidence(plan, asset.getRelativePath(), asset.getSha256(), contract);
    invalidateAcceptedFrames(plan);
    VisualReferenceAsset binding = VisualReferenceAsset.builder().plan(plan).role("FIRST_FRAME").sourceKind("EXISTING").renderAssetId(asset.getId()).relativePath(asset.getRelativePath()).sha256(asset.getSha256()).promptSha256(asset.getPromptHash()).validationStatus("METADATA_VERIFIED").validationEvidenceJson(json(evidence)).accepted(true).build();
    planAssets.save(binding);
    plan.setFirstFrameStatus("AVAILABLE_REVIEW_REQUIRED");
    plan.setValidationStatus("REVIEW_REQUIRED");
    plans.save(plan);
    return Map.of("planId", planId, "assetId", renderAssetId, "role", "FIRST_FRAME", "accepted", true, "semanticStatus", "UNKNOWN");
  }

  @Transactional
  public Map<String, Object> acceptImportedFirstFrame(UUID planId, UUID referenceAssetId) {
    return acceptImportedFirstFrame(planId, referenceAssetId, Map.of());
  }

  @Transactional
  public Map<String, Object> acceptImportedFirstFrame(UUID planId, UUID referenceAssetId, Map<String, Object> contract) {
    VisualReferencePlan plan = plans.findById(planId).orElseThrow(() -> new IllegalArgumentException("Visual reference plan not found"));
    VisualReferenceAsset binding = planAssets.findById(referenceAssetId).orElseThrow(() -> new IllegalArgumentException("Visual reference asset not found"));
    if (!planId.equals(binding.getPlan().getId()) || !"FIRST_FRAME".equals(binding.getRole())) throw new IllegalArgumentException("Reference asset is not a first-frame candidate for this plan");
    if (!plan.getPromptSha256().equals(binding.getPromptSha256())) throw new IllegalStateException("Uploaded first frame belongs to a different prompt version");
    if (!"METADATA_VERIFIED".equals(binding.getValidationStatus())) throw new IllegalStateException("Uploaded first frame needs technical validation before acceptance");
    var evidence = acceptanceEvidence(plan, binding.getRelativePath(), binding.getSha256(), contract);
    invalidateAcceptedFrames(plan);
    binding.setValidationEvidenceJson(json(evidence));
    binding.setAccepted(true);
    planAssets.save(binding);
    plan.setFirstFrameStatus("AVAILABLE_REVIEW_REQUIRED");
    plan.setValidationStatus("REVIEW_REQUIRED");
    plans.save(plan);
    return Map.of("planId", planId, "assetId", referenceAssetId, "role", "FIRST_FRAME", "accepted", true, "semanticStatus", "UNKNOWN");
  }

  private void invalidateAcceptedFrames(VisualReferencePlan plan) {
    for (var previous : planAssets.findByPlanIdOrderByCreatedAtAsc(plan.getId())) {
      if ("FIRST_FRAME".equals(previous.getRole()) && previous.isAccepted()) { previous.setAccepted(false); planAssets.save(previous); }
    }
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
    if (candidates.stream().anyMatch(a -> !job.getPromptSha256().equals(a.getPromptHash()))) return "MISMATCH_CONFIRMED";
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
    String action = switch (status) { case "MISSING" -> "PREPARE_FIRST_FRAME"; case "STALE", "MISMATCH_CONFIRMED" -> "REPLACE_STALE_FIRST_FRAME"; case "AVAILABLE_REVIEW_REQUIRED" -> "REVIEW_EXISTING_FIRST_FRAME"; default -> "COMPLETE_PROMPT"; };
    String constraints = job.getCompiledGenerationConstraints() == null ? "" : job.getCompiledGenerationConstraints().toLowerCase(java.util.Locale.ROOT);
    boolean difficultState = java.util.regex.Pattern.compile("transform|reveal|scale|spatial|contact|continuity|state change").matcher(constraints).find();
    String criticalScene = difficultState ? (capabilities.videoMultipleElementReferences() == OpenArtCapabilities.Support.SUPPORTED ? "FIRST_FRAME_PLUS_CRITICAL_REFERENCE_RECOMMENDED" : "ADDITIONAL_IMAGE_NOT_SUPPORTED") : "INSUFFICIENT_EVIDENCE";
    String reason = difficultState ? (criticalScene.equals("ADDITIONAL_IMAGE_NOT_SUPPORTED") ? "Structured constraints suggest a difficult visual state, but the active OpenArt video contract supports only one start image." : "Structured constraints identify a potentially difficult visual state; review one optional additional reference.") : "Use the fewest references necessary; no critical-scene image is recommended without structured beat evidence.";
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("strategy", strategy); result.put("action", action); result.put("criticalScene", criticalScene); result.put("reason", reason); result.put("additionalReferenceSupport", capabilities.videoMultipleElementReferences().name());
    result.put("criticalBeatId", difficultState ? "STRUCTURED_CONSTRAINT_BEAT" : "UNSPECIFIED_BEAT");
    result.put("narrativePosition", difficultState ? "CRITICAL_STATE_CHANGE" : "UNSPECIFIED");
    result.put("intendedState", difficultState ? "PRESERVE_IDENTITY_AND_ENVIRONMENT_WHILE_VERIFYING_THE_REQUIRED_STATE_CHANGE" : "UNSPECIFIED");
    return result;
  }

  private Map<String, Object> generationProposal(RenderJob job) {
    return Map.of("promptText", "Opening still for the accepted production prompt. Show the exact visible opening state, recognizable approved characters, required object and spatial relationships, consistent environment, child-appropriate presentation, and clear framing. Do not depict later transformations or the full video timeline.\n\nACCEPTED PRODUCTION PROMPT:\n" + job.getPromptTextSnapshot(), "model", job.getOpenartModel(), "referenceRoles", List.of("CHARACTER_REFERENCE", "SCENE_REFERENCE"), "aspectRatio", "FROM_APPROVED_RENDER_SETTINGS", "dimensions", "FROM_PROVIDER_CAPABILITY", "costStatus", "ESTIMATE_ONLY");
  }

  private Map<String, Object> modelCapabilities(String model) {
    com.fasterxml.jackson.databind.JsonNode selected = mapper.createObjectNode();
    String family = "UNKNOWN";
    String registryVersion = "Provider capability registry unavailable";
    try {
      var registry = mapper.readTree(dataRoot.resolve("workflow/provider-capabilities.json").toFile());
      var entries = registry.path("models").fields();
      while (entries.hasNext()) {
        var entry = entries.next();
        if (entry.getValue().path("apiModelId").asText().equals(model)) {
          selected = entry.getValue(); family = entry.getKey();
          registryVersion = selected.path("version").asText(registry.path("version").asText()); break;
        }
      }
    } catch (IOException ignored) { /* Missing registry is UNKNOWN, never supported. */ }
    var properties = selected.path("modes").path("image2video").path("properties");
    String start = properties.has("startFrame") ? "SUPPORTED" : "UNVERIFIED";
    String multiple = "UNSUPPORTED";
    String end = properties.has("endFrame") ? "SUPPORTED" : "UNVERIFIED";
    String modelFamily = family;
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("model", model == null ? "" : model);
    result.put("modelFamily", modelFamily);
    result.put("startFrame", start);
    result.put("endFrame", end);
    result.put("multipleVideoReferences", multiple);
    result.put("characterReferences", "UNVERIFIED");
    result.put("storyboard", "UNVERIFIED");
    result.put("segmentContinuation", "UNVERIFIED");
    result.put("duration", properties.has("duration") ? "SUPPORTED" : "UNVERIFIED");
    result.put("aspectRatio", properties.has("aspectRatio") ? "SUPPORTED" : "UNVERIFIED");
    result.put("resolution", properties.has("resolution") ? "SUPPORTED" : "UNVERIFIED");
    result.put("ordering", "SUPPORTED");
    result.put("intermediateKeyframe", "UNSUPPORTED");
    result.put("verificationSource", registryVersion);
    return result;
  }

  private Map<String, Object> capabilitiesMap(OpenArtCapabilities c) { return Map.of("imageMultipleReferences", c.imageMultipleReferences().name(), "videoSingleStartFrame", c.videoSingleStartFrame().name(), "videoMultipleElementReferences", c.videoMultipleElementReferences().name(), "workspaceAssetDiscovery", c.workspaceAssetDiscovery().name()); }
  private Map<String, Object> readObject(String json) { try { return mapper.readValue(json == null ? "{}" : json, new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {}); } catch (Exception ignored) { return Map.of(); } }
  private Map<String, Object> costMap() { BigDecimal frame = credits.getEstimatedCost(RenderJob.JobType.FIRST_FRAME); return Map.of("imageGenerationCredits", frame == null ? "UNKNOWN" : frame, "visionValidation", "UNKNOWN", "paidCallPerformed", false); }
  private Map<String, Object> assetView(RenderAsset a, RenderJob job) { return assetView(a, job.getPromptSha256()); }
  private Map<String, Object> assetView(RenderAsset a, String promptHash) {
    boolean matches = promptHash.equals(a.getPromptHash());
    boolean verified = Boolean.TRUE.equals(a.getMediaVerified()) && !Boolean.TRUE.equals(a.getQuarantined()) && fileExists(a);
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("assetId", a.getId()); result.put("role", "FIRST_FRAME");
    result.put("source", a.getSource() == null ? "UNKNOWN" : a.getSource());
    result.put("relativePath", a.getRelativePath()); result.put("sha256", a.getSha256() == null ? "" : a.getSha256());
    result.put("promptSha256", a.getPromptHash() == null ? "" : a.getPromptHash());
    result.put("promptVersionMatches", matches); result.put("mediaVerified", verified);
    result.put("quarantined", Boolean.TRUE.equals(a.getQuarantined()));
    result.put("eligible", matches && verified && a.getSha256() != null); result.put("semanticStatus", "UNKNOWN");
    return result;
  }
  private Map<String, Object> bindingView(VisualReferenceAsset asset) {
    Map<String, Object> view = new LinkedHashMap<>();
    view.put("assetId", asset.getId()); view.put("role", asset.getRole());
    view.put("sourceKind", asset.getSourceKind()); view.put("relativePath", asset.getRelativePath());
    view.put("sha256", asset.getSha256()); view.put("validationStatus", asset.getValidationStatus());
    view.put("accepted", asset.isAccepted()); view.put("createdAt", asset.getCreatedAt());
    try { view.put("evidence", mapper.readValue(asset.getValidationEvidenceJson(), Map.class)); }
    catch (Exception ignored) { view.put("evidence", Map.of()); }
    view.put("mediaUrl", "/api/v1/visual-reference-plans/" + asset.getPlan().getId() + "/assets/" + asset.getId() + "/media");
    return view;
  }

  @Transactional(readOnly = true)
  public Path referenceMedia(UUID planId, UUID assetId) {
    VisualReferenceAsset binding = planAssets.findById(assetId).orElseThrow(() -> new IllegalArgumentException("Visual reference asset not found"));
    if (!planId.equals(binding.getPlan().getId())) throw new IllegalArgumentException("Asset belongs to a different plan");
    return verifiedImagePath(binding.getRelativePath(), binding.getSha256());
  }

  private Path verifiedImagePath(String storedPath, String checksum) {
    if (storedPath == null || checksum == null) throw new IllegalStateException("Image provenance is missing");
    Path path = Path.of(storedPath);
    if (!path.isAbsolute()) path = dataRoot.resolve(path);
    path = path.toAbsolutePath().normalize();
    try {
      if (!path.toRealPath().startsWith(dataRoot.toRealPath()) || !Files.isRegularFile(path)) throw new IllegalStateException("Image is outside the asset store");
      byte[] bytes = Files.readAllBytes(path);
      if (!checksum.equals(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)))) throw new IllegalStateException("Image checksum changed; upload and accept the current image again");
      if (javax.imageio.ImageIO.read(path.toFile()) == null) throw new IllegalStateException("Asset is not a decodable image");
      return path;
    } catch (IOException | NoSuchAlgorithmException e) { throw new IllegalStateException("Stored image is unavailable", e); }
  }

  private Map<String, Object> acceptanceEvidence(VisualReferencePlan plan, String path, String checksum, Map<String, Object> contract) {
    var snapshot = content.fetch(plan.getContentId(), plan.getPromptVersionId());
    if (!plan.getPromptSha256().equals(snapshot.promptSha256())) throw new IllegalStateException("Plan prompt is stale");
    String ratio = String.valueOf(contract.getOrDefault("aspectRatio", ""));
    if (!List.of("9:16", "16:9", "1:1", "4:3", "3:4").contains(ratio)) throw new IllegalArgumentException("A supported target aspect ratio is required for acceptance");
    String model = String.valueOf(contract.getOrDefault("model", ""));
    if (!plan.getModel().equals(model)) throw new IllegalStateException("Selected generator differs from the saved visual plan");
    Path imagePath = verifiedImagePath(path, checksum);
    try {
      var image = javax.imageio.ImageIO.read(imagePath.toFile());
      String[] parts = ratio.split(":");
      double expected = Double.parseDouble(parts[0]) / Double.parseDouble(parts[1]);
      if (image.getWidth() < 64 || image.getHeight() < 64 || image.getWidth() > 8192 || image.getHeight() > 8192 || Math.abs((double) image.getWidth() / image.getHeight() / expected - 1) > .02) throw new IllegalArgumentException("Image dimensions do not match the target aspect ratio " + ratio);
      Map<String, Object> evidence = new LinkedHashMap<>();
      contract.forEach((key, value) -> evidence.put(key, value == null ? "" : value));
      evidence.put("width", image.getWidth()); evidence.put("height", image.getHeight());
      evidence.put("contentId", plan.getContentId()); evidence.put("promptVersionId", plan.getPromptVersionId());
      evidence.put("promptHash", plan.getPromptSha256()); evidence.put("checksum", checksum);
      evidence.put("acceptedAt", java.time.Instant.now().toString()); evidence.put("semanticStatus", "UNKNOWN");
      return evidence;
    } catch (IOException e) { throw new IllegalStateException("Image cannot be decoded", e); }
  }
  private String json(Object value) { try { return mapper.writeValueAsString(value); } catch (JsonProcessingException e) { throw new IllegalStateException("Could not serialize visual reference plan", e); } }
}
