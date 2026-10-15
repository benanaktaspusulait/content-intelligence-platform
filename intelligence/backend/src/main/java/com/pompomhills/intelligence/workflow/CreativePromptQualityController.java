package com.pompomhills.intelligence.workflow;

import jakarta.servlet.http.HttpServletRequest;
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

  @PostMapping("/records/{analysisId}/creative-prompt-quality/assess")
  public Map<String,Object> assessAll(@PathVariable UUID analysisId) { return service.assessAll(analysisId); }

  @PostMapping("/records/{analysisId}/candidates/{candidateId}/fidelity-review")
  public Map<String,Object> fidelityReview(@PathVariable UUID analysisId,@PathVariable String candidateId,
      @RequestBody Map<String,Object> request,HttpServletRequest principal) {
    return service.reviewFidelity(analysisId,candidateId,request,principal);
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
