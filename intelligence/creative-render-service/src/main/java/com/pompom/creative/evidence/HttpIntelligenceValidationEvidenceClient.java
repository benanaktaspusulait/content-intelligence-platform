package com.pompom.creative.evidence;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * Fetches validation evidence from the intelligence backend's internal evidence endpoint. Mirrors
 * {@code HttpIntelligenceContentClient}'s timeout/status-mapping pattern.
 */
@Component
public class HttpIntelligenceValidationEvidenceClient
    implements IntelligenceValidationEvidenceClient {
  private final RestClient restClient;

  public HttpIntelligenceValidationEvidenceClient(
      @Qualifier("intelligenceRestClient") RestClient restClient) {
    this.restClient = restClient;
  }

  @Override
  public ValidationEvidenceDto getEvidence(long validationRecordId) {
    try {
      return restClient
          .get()
          .uri("/api/v1/internal/validation-evidence/{validationRecordId}", validationRecordId)
          .retrieve()
          .onStatus(
              status -> status.value() == 404,
              (request, response) -> {
                throw new ValidationEvidenceNotFoundException(validationRecordId);
              })
          .onStatus(
              status -> status.value() == 422,
              (request, response) -> {
                throw new ValidationEvidenceIncompleteRemoteException(validationRecordId);
              })
          .onStatus(
              HttpStatusCode::is5xxServerError,
              (request, response) -> {
                throw new ValidationEvidenceServiceException(
                    "Intelligence service failed with status " + response.getStatusCode().value());
              })
          .body(ValidationEvidenceDto.class);
    } catch (ResourceAccessException error) {
      if (isTimeout(error)) {
        throw new ValidationEvidenceTimeoutException(validationRecordId, error);
      }
      throw new ValidationEvidenceServiceException("Intelligence service is unavailable", error);
    }
  }

  @Override
  public VisualEvidenceSubmissionResponse submitVisualEvidence(
      VisualEvidenceSubmissionDto request) {
    try {
      return restClient
          .post()
          .uri(
              "/api/v1/internal/validation-evidence/{validationRecordId}/visual",
              request.validationRecordId())
          .body(request)
          .retrieve()
          .onStatus(
              status -> status.value() == 404,
              (httpRequest, response) -> {
                throw new ValidationEvidenceServiceException("Validation record not found");
              })
          .onStatus(
              status -> status.value() == 409,
              (httpRequest, response) -> {
                throw new ValidationEvidenceServiceException("Visual evidence conflict");
              })
          .onStatus(
              status -> status.value() == 422,
              (httpRequest, response) -> {
                throw new ValidationEvidenceServiceException("Invalid visual evidence");
              })
          .onStatus(
              HttpStatusCode::is5xxServerError,
              (httpRequest, response) -> {
                throw new ValidationEvidenceServiceException(
                    "Intelligence service failed with status " + response.getStatusCode().value());
              })
          .body(VisualEvidenceSubmissionResponse.class);
    } catch (ResourceAccessException error) {
      throw new ValidationEvidenceServiceException("Intelligence service is unavailable", error);
    }
  }

  private boolean isTimeout(Throwable error) {
    Throwable current = error;
    while (current != null) {
      if (current instanceof SocketTimeoutException || current instanceof HttpTimeoutException) {
        return true;
      }
      current = current.getCause();
    }
    return false;
  }
}
