package com.pompomhills.intelligence.content;

import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/intelligence/contents")
public class InternalContentPromptController {
  private static final URI NOT_FOUND_TYPE =
      URI.create("https://pompomhills.com/problems/content-prompt-not-found");

  private final ContentPromptQueryService service;

  public InternalContentPromptController(ContentPromptQueryService service) {
    this.service = service;
  }

  @GetMapping("/{contentId}/prompt-versions/{promptVersionId}")
  public ContentPromptSnapshot load(
      @PathVariable long contentId, @PathVariable long promptVersionId) {
    return service.load(contentId, promptVersionId);
  }

  @ExceptionHandler(ContentPromptNotFoundException.class)
  ResponseEntity<ProblemDetail> notFound(ContentPromptNotFoundException error) {
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, error.getMessage());
    problem.setTitle("Content prompt snapshot not found");
    problem.setType(NOT_FOUND_TYPE);
    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem);
  }
}
