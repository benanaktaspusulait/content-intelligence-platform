package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;

class ValidationEvidenceControllerTest {

  private ValidationEvidenceService service;
  private ValidationEvidenceController controller;

  @BeforeEach
  void setUp() {
    service = mock(ValidationEvidenceService.class);
    controller = new ValidationEvidenceController(service);
  }

  @Test
  void returnsEvidenceForCompleteRecord() {
    ValidationEvidenceResponse evidence = completeResponse();
    when(service.getEvidence(42L)).thenReturn(evidence);

    ValidationEvidenceResponse result = controller.getEvidence(42L);

    assertThat(result).isEqualTo(evidence);
  }

  @Test
  void mapsNotFoundToStableProblemCode() {
    ValidationEvidenceNotFoundException error = new ValidationEvidenceNotFoundException(404L);

    ResponseEntity<ProblemDetail> response = controller.notFound(error);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    assertThat(response.getBody().getProperties())
        .containsEntry("errorCode", ValidationEvidenceNotFoundException.ERROR_CODE);
    // No prompt body should ever appear in an error response.
    assertThat(response.getBody().getDetail()).doesNotContain("prompt");
  }

  @Test
  void mapsIncompleteToStableProblemCode() {
    ValidationEvidenceIncompleteException error =
        new ValidationEvidenceIncompleteException(7L, "contentId is missing");

    ResponseEntity<ProblemDetail> response = controller.incomplete(error);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY);
    assertThat(response.getBody().getProperties())
        .containsEntry("errorCode", ValidationEvidenceIncompleteException.ERROR_CODE);
  }

  private ValidationEvidenceResponse completeResponse() {
    return new ValidationEvidenceResponse(
        42L,
        10L,
        11L,
        "a".repeat(64),
        ValidationDecisionStatus.RENDER_READY,
        0,
        0,
        0,
        "1.0",
        "openai",
        "gpt-4o-2026-01",
        "1.0",
        UUID.randomUUID(),
        Instant.now(),
        Instant.now(),
        Instant.now().plusSeconds(3600));
  }
}
