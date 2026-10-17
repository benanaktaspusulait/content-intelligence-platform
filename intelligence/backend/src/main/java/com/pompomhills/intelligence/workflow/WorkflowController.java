package com.pompomhills.intelligence.workflow;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow")
public class WorkflowController {
  private final WorkflowService service;
  @org.springframework.beans.factory.annotation.Autowired private Step6GovernanceService governance;
  @org.springframework.beans.factory.annotation.Autowired private StoryEvolutionService storyEvolution;

  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.quality.QualityReportPdfService pdf;

  public WorkflowController(WorkflowService service) {
    this.service = service;
  }

  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.quality.IntelligenceQualityValidationService
      canonicalValidation;

  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.content.ContentWorkspaceController contents;

  @org.springframework.beans.factory.annotation.Autowired
  private CreativePromptQualityService cpq;

  @PostMapping("/records/{id}/canonical-validation")
  public com.pompomhills.intelligence.quality.IntelligenceValidateResponse canonicalValidation(
      @PathVariable UUID id) {
    return canonicalValidation.validateWorkflowProfile(service.getByKind(id, "REVIEW"));
  }

  @GetMapping("/records/{id}/creative-optimization/latest")
  public Map<String, Object> latestCreativeOptimization(@PathVariable UUID id) {
    return service.latestCreativeOptimization(id);
  }

  @GetMapping("/records/{id}/creative-optimization/history")
  public List<Map<String,Object>> creativeOptimizationHistory(@PathVariable UUID id) {
    var comparisons=service.creativeOptimizationHistory(id);
    for(var comparison:comparisons) {
      UUID comparisonId=UUID.fromString(String.valueOf(comparison.get("recordId")));
      comparison.put("candidateBindings",cpq.comparisonBindings(id,comparisonId).get("candidateBindings"));
      comparison.put("historical",!comparison.equals(comparisons.getFirst()));
    }
    return comparisons;
  }

  @PostMapping("/records/{id}/creative-optimization/revalidate")
  public Map<String,Object> revalidateCreativeOptimization(@PathVariable UUID id, @RequestBody Map<String,Object> request) {
    if (!(request.get("sourceComparisonId") instanceof String comparisonId))
      throw new IllegalArgumentException("sourceComparisonId is required");
    return service.revalidateCreativeOptimization(id, UUID.fromString(comparisonId));
  }

  @GetMapping("/records/{id}/creative-optimization/preflight")
  public Map<String,Object> adaptiveOptimizationPreflight(@PathVariable UUID id) {
    return service.adaptiveOptimizationPreflight(id);
  }

  @PostMapping("/records/{id}/creative-optimization")
  public org.springframework.http.ResponseEntity<Map<String,Object>> creativeOptimization(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    if (!(request.get("contentId") instanceof Number contentId)
        || !(request.get("promptVersionId") instanceof Number promptVersionId))
      throw new IllegalArgumentException("contentId and promptVersionId are required");
    var provenance = contents.creativeProvenance(contentId.longValue(), promptVersionId.longValue());
    var result = service.generateCreativeOptimization(id, request, provenance);
    if (Boolean.TRUE.equals(result.get("optimizationFailed"))) {
      var status="UNRESOLVED_ATTEMPT".equals(result.get("category")) || "PROVIDER_OUTCOME_UNKNOWN".equals(result.get("attemptState")) ? org.springframework.http.HttpStatus.BAD_GATEWAY : org.springframework.http.HttpStatus.CONFLICT;
      return org.springframework.http.ResponseEntity.status(status).body(result);
    }
    return org.springframework.http.ResponseEntity.ok(result);
  }

  @GetMapping("/learning/retrieve")
  public List<Map<String, Object>> retrieve(
      @RequestParam String contentProfile,
      @RequestParam String modelVersion,
      @RequestParam double duration,
      @RequestParam(defaultValue = "AUTO") String generator,
      @RequestParam(defaultValue = "{}") String settings) {
    try {
      var context = new java.util.LinkedHashMap<String, Object>();
      context.put("generator", generator);
      var parsed = new com.fasterxml.jackson.databind.ObjectMapper().readValue(settings, Map.class);
      if (!parsed.isEmpty()) context.put("settings", parsed);
      return service.retrieveLessons(contentProfile, modelVersion, duration, context);
    } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
      throw new IllegalArgumentException("Settings must be a JSON object", invalid);
    }
  }

  @PostMapping("/regeneration-handoff")
  public Map<String, Object> regenerationHandoff(@RequestBody Map<String, Object> request) {
    return service.regenerationHandoff(request);
  }

  @GetMapping("/creative-role/readiness")
  public Map<String, Object> creativeRoleReadiness() {
    return service.creativeRoleReadiness();
  }

  @PostMapping("/creative-role")
  public Map<String, Object> creativeRole(@RequestBody Map<String, Object> request) {
    return service.creativeRole(request);
  }

  @PostMapping("/records/{id}/revalidate-production-spec")
  public Map<String, Object> revalidateProductionSpec(@PathVariable UUID id) {
    return service.revalidateProductionSpec(id);
  }

  @PostMapping("/creative-role/{id}/approve-story")
  public Map<String, Object> approveStory(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.approveStory(id, request);
  }

  @PostMapping("/records/{id}/story-revisions")
  public Map<String, Object> saveStoryRevision(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.saveStoryRevision(id, request);
  }

  @PostMapping("/studio-sessions")
  public Map<String, Object> createStudioSession(@RequestBody Map<String, Object> request) {
    return service.saveStudioSession(request);
  }

  @GetMapping("/studio-sessions/{id}")
  public Map<String, Object> studioSession(@PathVariable UUID id) {
    return service.getStudioSession(id);
  }

  @PutMapping("/studio-sessions/{id}")
  public Map<String, Object> updateStudioSession(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    request = new java.util.LinkedHashMap<>(request);
    request.put("sessionId", id.toString());
    return service.saveStudioSession(request);
  }

  @GetMapping("/studio-sessions/by-prompt")
  public Map<String, Object> studioSessionForPrompt(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    return service.getStudioSessionForPrompt(contentId, promptVersionId);
  }

  @PostMapping("/production-settings")
  public Map<String, Object> productionSettings(@RequestBody Map<String, Object> request) {
    return service.saveProductionSettings(request);
  }

  @GetMapping("/production-settings")
  public Map<String, Object> productionSettingsForPrompt(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    return service.getProductionSettings(contentId, promptVersionId);
  }

  @GetMapping("/provider-capabilities")
  public Map<String, Object> providerCapabilities() {
    return service.getProviderCapabilities();
  }

  @GetMapping("/production-review/decisions")
  public Map<String, Object> productionReviewDecisions(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    return service.getProductionReviewDecisions(contentId, promptVersionId);
  }

  @GetMapping("/records/{id}/governance")
  public Map<String,Object> governance(@PathVariable UUID id, jakarta.servlet.http.HttpServletRequest request) {
    return governance.evaluate(id, Step6GovernanceService.Actor.from(request));
  }

  @PostMapping("/cpq/story-evolution-runs")
  public Map<String,Object> startStoryEvolution(@RequestBody Map<String,Object> request, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.start(request,http); }

  @PostMapping("/cpq/story-evolution-preflight")
  public Map<String,Object> inspectStoryEvolution(@RequestBody Map<String,Object> request, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.inspectPilot(request,http); }

  @PostMapping("/cpq/story-assessment-preflight")
  public Map<String,Object> inspectStoryAssessment(@RequestBody Map<String,Object> request, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.inspectAssessment(request,http); }

  @GetMapping("/cpq/story-evolution-source")
  public Map<String,Object> storyEvolutionSource(@RequestParam UUID analysisId) {
    var subject=cpq.pilotSubject(analysisId,null,null); var story=CpqOwnerPilotService.map(subject.get("approvedStory"));
    var review=service.getByKind(analysisId,"REVIEW");
    var out=new java.util.LinkedHashMap<String,Object>(); out.put("analysisId",analysisId.toString()); out.put("contentId",review.get("contentId")); out.put("promptVersionId",review.get("promptVersionId")); out.put("storyRecordId",story.get("storyId")); out.put("story",story.get("text")); out.put("storySha256",CpqOwnerPilotService.hash(String.valueOf(story.get("text")))); out.put("approvalRecordId",story.get("approvalRecordId")); out.put("canonical",subject.get("canonical")); out.put("productionSettings",subject.get("productionSettings")); return out;
  }

  @GetMapping("/cpq/story-evolution-runs/{id}")
  public Map<String,Object> storyEvolution(@PathVariable UUID id, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.view(id,http); }

  @GetMapping("/cpq/story-evolution-runs/latest")
  public Map<String,Object> latestStoryEvolution(@RequestParam UUID sourceStoryRecordId, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.latest(sourceStoryRecordId,http); }

  @PostMapping("/cpq/story-evolution-runs/{id}/approve")
  public Map<String,Object> approveStoryEvolution(@PathVariable UUID id, @RequestBody Map<String,Object> request, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.approve(id,request,http); }

  @PostMapping("/cpq/story-evolution-runs/{id}/prompt-handoff")
  public Map<String,Object> storyEvolutionPromptHandoff(@PathVariable UUID id, @RequestBody Map<String,Object> request, jakarta.servlet.http.HttpServletRequest http) { return storyEvolution.handoff(id,request,http); }

  @PostMapping("/cpq/story-evolution-runs/{id}/stop")
  public Map<String,Object> stopStoryEvolution(@PathVariable UUID id, jakarta.servlet.http.HttpServletRequest http) { storyEvolution.owner(id,http); return storyEvolution.stop(id,"CANCELLED",""); }

  @PostMapping("/records/{id}/governance/{action}")
  public Map<String,Object> governanceCommand(@PathVariable UUID id, @PathVariable String action,
      @RequestBody Map<String,Object> body, jakarta.servlet.http.HttpServletRequest request) {
    return governance.command(id, action, body, Step6GovernanceService.Actor.from(request));
  }

  @PostMapping("/production-review/decisions")
  public Map<String, Object> saveProductionReviewDecision(@RequestBody Map<String, Object> request,
      jakarta.servlet.http.HttpServletRequest httpRequest) {
    if ("NO_TEXT_REPAIR_JUSTIFIED".equals(request.get("decisionType")))
      return governance.command(UUID.fromString(String.valueOf(request.get("analysisRunId"))),
          "text-acceptance", request, Step6GovernanceService.Actor.from(httpRequest));
    return service.saveProductionReviewDecision(request);
  }

  @GetMapping("/production-review/reference-binding")
  public Map<String, Object> productionReferenceBinding(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    return service.getProductionReferenceBinding(contentId, promptVersionId);
  }

  @PostMapping("/production-review/reference-binding")
  public Map<String, Object> saveProductionReferenceBinding(@RequestBody Map<String, Object> request) {
    return service.saveProductionReferenceBinding(request);
  }

  @PostMapping("/visual-preparation")
  public Map<String, Object> visualPreparation(@RequestBody Map<String, Object> request) {
    return service.saveVisualPreparation(request);
  }

  @GetMapping("/visual-preparation")
  public org.springframework.http.ResponseEntity<Map<String, Object>> visualPreparationForPrompt(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    try {
      return org.springframework.http.ResponseEntity.ok(
          service.getVisualPreparation(contentId, promptVersionId));
    } catch (IllegalArgumentException missing) {
      return org.springframework.http.ResponseEntity.notFound().build();
    }
  }

  /** Generate a start-frame candidate image from the saved production prompt. */
  @PostMapping("/start-frame/generate")
  public Map<String, Object> generateStartFrame(@RequestBody Map<String, Object> request) {
    return service.generateStartFrame(request);
  }

  /** List start-frame candidates for a content/prompt version. */
  @GetMapping("/start-frame/candidates")
  public Map<String, Object> listStartFrameCandidates(
      @RequestParam Long contentId, @RequestParam Long promptVersionId) {
    return service.listStartFrameCandidates(contentId, promptVersionId);
  }

  /** Accept a start-frame candidate. */
  @PostMapping("/start-frame/accept")
  public Map<String, Object> acceptStartFrame(@RequestBody Map<String, Object> request) {
    return service.acceptStartFrame(request);
  }

  /** Reject a start-frame candidate. */
  @PostMapping("/start-frame/reject")
  public Map<String, Object> rejectStartFrame(@RequestBody Map<String, Object> request) {
    return service.rejectStartFrame(request);
  }

  @PostMapping("/review")
  public Map<String, Object> review(@RequestBody WorkflowService.ReviewRequest request) {
    return service.runReview(request, true);
  }

  @GetMapping("/records/{id}")
  public Map<String, Object> record(@PathVariable UUID id) {
    return service.get(id);
  }

  @GetMapping("/records")
  public List<Map<String, Object>> records(
      @RequestParam(defaultValue = "REVIEW") String kind,
      @RequestParam(required = false) String contentId,
      @RequestParam(required = false) String promptVersionId,
      @RequestParam(required = false) String bindingHash) {
    return service.list(kind, contentId, promptVersionId, bindingHash);
  }

  @PostMapping("/records/{id}/lifecycle")
  public Map<String, Object> lifecycle(@PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.changeLifecycle(id, request);
  }

  @PostMapping("/records/{id}/duplicate")
  public Map<String, Object> duplicate(@PathVariable UUID id) {
    return service.duplicateCreativeRole(id);
  }

  @GetMapping(value = "/records/{id}/pdf", produces = "application/pdf")
  public org.springframework.http.ResponseEntity<byte[]> report(@PathVariable UUID id) {
    var snapshot = service.get(id);
    boolean analysis = snapshot.containsKey("boundRequest") || snapshot.containsKey("canonicalRuleEvaluation");
    return org.springframework.http.ResponseEntity.ok()
        .header("Content-Disposition", "attachment; filename=pompom-analysis-" + id + ".pdf")
        .header("Cache-Control", "no-store")
        .body(analysis ? pdf.renderFullAnalysis(sourcePlanForExport(id), snapshot) : pdf.renderWorkflow(snapshot));
  }

  @GetMapping("/records/{id}/source-plan")
  public Map<String, Object> sourcePlan(@PathVariable UUID id) {
    return service.sourcePlan(id);
  }

  private Map<String, Object> sourcePlanForExport(UUID id) {
    try {
      return service.sourcePlan(id);
    } catch (RuntimeException unavailable) {
      return Map.of("kind", "READ_ONLY_SOURCE_EXTRACTION", "status", "UNKNOWN",
          "historicalRunId", id.toString(), "reason", "Current parser projection unavailable; historical evidence is preserved.");
    }
  }

  @PostMapping("/records/{id}/repair")
  public Map<String, Object> repair(@PathVariable UUID id, @RequestBody Repair request) {
    return service.repair(id, request.patches());
  }

  @PostMapping("/records/{id}/qa")
  public Map<String, Object> qa(@PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.actualQa(id, request);
  }

  @PostMapping("/videos/{videoId}/edited-variant")
  public Map<String, Object> importEdit(
      @PathVariable UUID videoId, @RequestBody Map<String, Object> request) {
    return service.importEditedVariant(videoId, request);
  }

  @GetMapping("/videos/{videoId}/edit-handoffs")
  public List<Map<String, Object>> editedHandoffs(@PathVariable UUID videoId) {
    return service.editedHandoffs(videoId);
  }

  @GetMapping("/videos/{videoId}/qa")
  public List<Map<String, Object>> actualQaRecords(@PathVariable UUID videoId) {
    return service.actualQaRecords(videoId);
  }

  @PostMapping("/videos/{videoId}/qa")
  public Map<String, Object> qaWithoutPlan(
      @PathVariable UUID videoId, @RequestBody Map<String, Object> request) {
    return service.actualQaWithoutPlan(videoId, request);
  }

  @PostMapping("/feedback/{kind}")
  public Map<String, Object> feedback(
      @PathVariable String kind, @RequestBody Map<String, Object> request) {
    return service.feedback(kind, request);
  }

  @PostMapping("/learning/{kind}")
  public Map<String, Object> learning(
      @PathVariable String kind, @RequestBody Map<String, Object> request) {
    return service.lesson(kind, request);
  }

  @PostMapping("/records/{id}/admission")
  public Map<String, Object> admission(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.admission(id, request);
  }

  @PostMapping("/records/{id}/critic")
  public Map<String, Object> critic(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.secondOpinion(id, request);
  }

  @PostMapping("/records/{id}/learning-review")
  public Map<String, Object> learningReview(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.reviewLearning(id, request);
  }

  @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
  public org.springframework.http.ResponseEntity<Map<String, Object>> invalid(
      RuntimeException error) {
    return org.springframework.http.ResponseEntity.status(409)
        .body(Map.of("status", "UNKNOWN", "detail", error.getMessage()));
  }

  public record Repair(List<Map<String, Object>> patches) {}
}
