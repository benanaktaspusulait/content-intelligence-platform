package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.content.ContentPromptNotFoundException;
import java.util.List;
import java.util.Map;
import org.hamcrest.Matchers;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class IntelligenceQualityValidationControllerTest {

  private IntelligenceQualityValidationService service;
  private IntelligenceQualityValidationController controller;
  private MockMvc mvc;

  @BeforeEach
  void setUp() {
    service = mock(IntelligenceQualityValidationService.class);
    controller = new IntelligenceQualityValidationController(service);
    mvc = MockMvcBuilders.standaloneSetup(controller).build();
  }

  @Test
  void malformedJsonBodyNeverEchoesRequestContentBackInTheErrorResponse() throws Exception {
    String bodyContainingASecretLikeString =
        "{\"prompt\": \"super-secret-prompt-text-that-must-never-leak\", this is not valid json";

    mvc.perform(
            post("/api/v1/intelligence/quality/validate")
                .contentType(MediaType.APPLICATION_JSON)
                .content(bodyContainingASecretLikeString))
        .andExpect(status().is4xxClientError())
        .andExpect(
            content()
                .string(
                    Matchers.not(
                        Matchers.containsString("super-secret-prompt-text-that-must-never-leak"))));
  }

  @Test
  void blankStandalonePromptOverHttpReturnsBadRequestWithoutEchoingThePrompt() throws Exception {
    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("secret-prompt-body-value", null, null, null);
    when(service.validateAndPersistEvidence(any()))
        .thenThrow(new IllegalArgumentException("Prompt text cannot be blank"));

    mvc.perform(
            post("/api/v1/intelligence/quality/validate")
                .contentType(MediaType.APPLICATION_JSON)
                .content(new ObjectMapper().writeValueAsString(request)))
        .andExpect(status().isBadRequest())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(
            content().string(Matchers.not(Matchers.containsString("secret-prompt-body-value"))));
  }

  @Test
  void returnsTheValidationResponseIncludingTheRecordId() {
    IntelligenceValidateRequest request =
        new IntelligenceValidateRequest("x".repeat(150), "1.0", 10L, 11L);
    IntelligenceValidateResponse expected = new IntelligenceValidateResponse(42L, sampleReport());
    when(service.validateAndPersistEvidence(request)).thenReturn(expected);

    ResponseEntity<IntelligenceValidateResponse> response = controller.validate(request);

    assertThat(response.getBody().validationRecordId()).isEqualTo(42L);
  }

  @Test
  void mapsContentPromptNotFoundToAProblemResponse() {
    ContentPromptNotFoundException error = new ContentPromptNotFoundException(10L, 999L);

    ResponseEntity<ProblemDetail> response = controller.contentPromptNotFound(error);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
  }

  @Test
  void mapsInvalidStandalonePromptToABadRequestResponse() {
    IllegalArgumentException error = new IllegalArgumentException("Prompt text cannot be blank");

    ResponseEntity<ProblemDetail> response = controller.invalidRequest(error);

    assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    assertThat(response.getBody().getDetail()).isEqualTo("Prompt text cannot be blank");
  }

  private QualityReportDto sampleReport() {
    return new QualityReportDto(
        95.0,
        "RENDER_READY",
        "1.0",
        0,
        0,
        0,
        Map.of(),
        List.of(),
        List.of(),
        List.of(),
        List.of(),
        List.of(),
        new ScoreCardDto(95.0, "Excellent", "green"),
        new TimelineDataDto(List.of(), List.of(), List.of()),
        1.0,
        List.of(),
        List.of(),
        List.of(),
        List.of(),
        List.of());
  }
}
