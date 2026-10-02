package com.pompomhills.intelligence.quality;

import com.pompomhills.intelligence.content.ContentPromptNotFoundException;
import jakarta.validation.Valid;
import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Public validation entry point that persists immutable evidence. This is the endpoint
 * creative-render-service's evidence requirement is built on: only validations submitted here (and
 * linked to a real content/prompt version) can ever become render-authorizing. The older {@link
 * QualityValidationController} remains available for ad hoc / exploratory scoring but never
 * produces render-authorizing evidence - see its class documentation.
 */
@RestController
@RequestMapping("/api/v1/intelligence/quality")
public class IntelligenceQualityValidationController {

  private static final URI CONTENT_PROMPT_NOT_FOUND_TYPE =
      URI.create("https://pompomhills.com/problems/content-prompt-not-found");

  private final IntelligenceQualityValidationService service;

  public IntelligenceQualityValidationController(IntelligenceQualityValidationService service) {
    this.service = service;
  }

  @PostMapping("/validate")
  public ResponseEntity<IntelligenceValidateResponse> validate(
      @Valid @RequestBody IntelligenceValidateRequest request) {
    return ResponseEntity.ok(service.validateAndPersistEvidence(request));
  }

  @ExceptionHandler(ContentPromptNotFoundException.class)
  ResponseEntity<ProblemDetail> contentPromptNotFound(ContentPromptNotFoundException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, error.getMessage());
    problem.setTitle("Content prompt version not found");
    problem.setType(CONTENT_PROMPT_NOT_FOUND_TYPE);
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
  }

  @ExceptionHandler(IllegalArgumentException.class)
  ResponseEntity<ProblemDetail> invalidRequest(IllegalArgumentException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, error.getMessage());
    problem.setTitle("Invalid validation request");
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(problem);
  }
}
