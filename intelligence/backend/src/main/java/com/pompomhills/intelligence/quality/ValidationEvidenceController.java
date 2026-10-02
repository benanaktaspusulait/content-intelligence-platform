package com.pompomhills.intelligence.quality;

import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Internal endpoint publishing immutable validation evidence to creative-render-service's render
 * queue gate. Never includes prompt text or other sensitive content in its responses or in error
 * problem details.
 */
@RestController
@RequestMapping("/api/v1/internal/validation-evidence")
public class ValidationEvidenceController {

  private static final URI NOT_FOUND_TYPE =
      URI.create("https://pompomhills.com/problems/validation-evidence-not-found");
  private static final URI INCOMPLETE_TYPE =
      URI.create("https://pompomhills.com/problems/validation-evidence-incomplete");

  private final ValidationEvidenceService service;

  public ValidationEvidenceController(ValidationEvidenceService service) {
    this.service = service;
  }

  @GetMapping("/{validationRecordId}")
  public ValidationEvidenceResponse getEvidence(@PathVariable long validationRecordId) {
    return service.getEvidence(validationRecordId);
  }

  @ExceptionHandler(ValidationEvidenceNotFoundException.class)
  ResponseEntity<ProblemDetail> notFound(ValidationEvidenceNotFoundException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND,
            "No validation record exists with id %d".formatted(error.getValidationRecordId()));
    problem.setTitle("Validation evidence not found");
    problem.setType(NOT_FOUND_TYPE);
    problem.setProperty("errorCode", ValidationEvidenceNotFoundException.ERROR_CODE);
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
  }

  @ExceptionHandler(ValidationEvidenceIncompleteException.class)
  ResponseEntity<ProblemDetail> incomplete(ValidationEvidenceIncompleteException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(
            HttpStatus.UNPROCESSABLE_ENTITY,
            "Validation record %d does not contain complete evidence"
                .formatted(error.getValidationRecordId()));
    problem.setTitle("Validation evidence incomplete");
    problem.setType(INCOMPLETE_TYPE);
    problem.setProperty("errorCode", ValidationEvidenceIncompleteException.ERROR_CODE);
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY).body(problem);
  }
}
