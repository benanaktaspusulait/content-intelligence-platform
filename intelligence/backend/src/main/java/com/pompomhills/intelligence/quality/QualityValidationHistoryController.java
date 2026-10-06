package com.pompomhills.intelligence.quality;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Lets the UI restore a prompt's previous analysis instead of re-running validation. */
@RestController
@RequestMapping("/api/v1/intelligence/quality/validations")
@Tag(name = "Quality Validation History", description = "Previously stored quality analyses")
public class QualityValidationHistoryController {

  private final QualityValidationHistoryService service;

  public QualityValidationHistoryController(QualityValidationHistoryService service) {
    this.service = service;
  }

  @PostMapping("/latest")
  @Operation(
      summary = "Get the latest stored analysis for a prompt",
      description =
          "Returns 200 with the stored report, or 204 when the prompt has not been analysed yet.")
  public ResponseEntity<StoredValidationResponse> latest(
      @RequestBody LatestValidationRequest request) {
    return service
        .findLatest(request)
        .map(ResponseEntity::ok)
        .orElseGet(() -> ResponseEntity.noContent().build());
  }

  @ExceptionHandler(IllegalArgumentException.class)
  ResponseEntity<ProblemDetail> invalidRequest(IllegalArgumentException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, error.getMessage());
    problem.setTitle("Invalid lookup request");
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(problem);
  }
}
