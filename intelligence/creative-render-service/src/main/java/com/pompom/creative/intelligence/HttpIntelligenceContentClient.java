package com.pompom.creative.intelligence;

import java.net.SocketTimeoutException;
import java.net.http.HttpTimeoutException;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

@Component
public class HttpIntelligenceContentClient implements IntelligenceContentClient {
  private final RestClient restClient;

  public HttpIntelligenceContentClient(@Qualifier("intelligenceRestClient") RestClient restClient) {
    this.restClient = restClient;
  }

  @Override
  public ContentPromptSnapshot fetch(long contentId, long promptVersionId) {
    try {
      return restClient
          .get()
          .uri(
              "/api/v1/intelligence/contents/{contentId}/prompt-versions/{promptVersionId}",
              contentId,
              promptVersionId)
          .retrieve()
          .onStatus(
              status -> status.value() == 404,
              (request, response) -> {
                throw new IntelligenceContentNotFoundException(contentId, promptVersionId);
              })
          .onStatus(
              status -> status.value() == 409,
              (request, response) -> {
                throw new IntelligenceContentConflictException(contentId, promptVersionId);
              })
          .onStatus(
              HttpStatusCode::is5xxServerError,
              (request, response) -> {
                throw new IntelligenceContentServiceException(
                    "Intelligence service failed with status " + response.getStatusCode().value());
              })
          .body(ContentPromptSnapshot.class);
    } catch (ResourceAccessException error) {
      if (isTimeout(error)) {
        throw new IntelligenceContentTimeoutException(contentId, promptVersionId, error);
      }
      throw new IntelligenceContentServiceException("Intelligence service is unavailable", error);
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
