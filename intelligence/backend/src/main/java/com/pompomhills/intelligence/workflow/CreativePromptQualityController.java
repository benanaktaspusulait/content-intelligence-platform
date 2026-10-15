package com.pompomhills.intelligence.workflow;

import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow")
public class CreativePromptQualityController {
  private final CreativePromptQualityService service;
  public CreativePromptQualityController(CreativePromptQualityService service) { this.service=service; }

  @GetMapping("/records/{analysisId}/creative-prompt-quality")
  public Map<String,Object> savedAssessments(@PathVariable UUID analysisId) { return service.savedAssessments(analysisId); }

  @GetMapping("/records/{analysisId}/comparisons/{comparisonId}/creative-prompt-quality/binding")
  public Map<String,Object> comparisonBinding(@PathVariable UUID analysisId,@PathVariable UUID comparisonId) {
    return service.comparisonBindings(analysisId,comparisonId);
  }

  @PostMapping("/records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/creative-prompt-quality/assess")
  public Map<String,Object> assess(@PathVariable UUID analysisId,@PathVariable UUID comparisonId,@PathVariable String candidateId,
      jakarta.servlet.http.HttpServletRequest principal) {
    var assessment=service.assess(analysisId,comparisonId,candidateId,principal);
    return Map.of("rubricVersion",CreativePromptQualityService.RUBRIC,"gradingStatus","CALIBRATION_INCOMPLETE",
        "absoluteQualityTarget","A_OR_A_PLUS","candidateAssessments",List.of(assessment),
        "originalCanonical",assessment.get("canonicalValidation"),"renderReadiness",assessment.get("renderReadiness"),
        "activationState","INACTIVE","comparisonId",comparisonId.toString());
  }

  @PostMapping("/records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/fidelity-review")
  public Map<String,Object> fidelityReview(@PathVariable UUID analysisId,@PathVariable UUID comparisonId,@PathVariable String candidateId,
      @RequestBody Map<String,Object> request,HttpServletRequest principal) {
    return service.reviewFidelity(analysisId,comparisonId,candidateId,request,principal);
  }

  @GetMapping("/cpq/calibration")
  public Map<String,Object> calibrationState() { return service.calibrationState(); }

  @GetMapping("/cpq/reviewer-capabilities")
  public Map<String,Object> reviewerCapabilities(HttpServletRequest principal) { return service.reviewerCapabilities(principal); }

  @PostMapping("/cpq/calibration/corpora/{version}")
  public Map<String,Object> createCorpus(@PathVariable String version,@RequestBody Map<String,Object> request,HttpServletRequest principal) {
    return service.createCorpus(version,request,principal);
  }

  @PostMapping("/cpq/calibration/corpora/{version}/examples")
  public Map<String,Object> addExample(@PathVariable String version,@RequestBody Map<String,Object> request,HttpServletRequest principal) {
    return service.addCalibrationExample(version,request,principal);
  }

  @GetMapping("/cpq/calibration/examples/{exampleId}/blind-review")
  public Map<String,Object> reviewPacket(@PathVariable UUID exampleId,HttpServletRequest principal) {
    return service.calibrationReviewPacket(exampleId,principal);
  }

  @PostMapping("/cpq/calibration/examples/{exampleId}/judgments")
  public Map<String,Object> judgment(@PathVariable UUID exampleId,@RequestBody Map<String,Object> request,HttpServletRequest principal) {
    return service.submitCalibrationJudgment(exampleId,request,principal);
  }

  @GetMapping("/cpq/calibration/corpora/{version}/readiness")
  public Map<String,Object> readiness(@PathVariable String version) { return service.calibrationReadiness(version); }

  @PostMapping("/cpq/calibration/corpora/{version}/preview")
  public Map<String,Object> calibrationPreview(@PathVariable String version,HttpServletRequest principal) { return service.calibrationPreview(version,principal); }
}
