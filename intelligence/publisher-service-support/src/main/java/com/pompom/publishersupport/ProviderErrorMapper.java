package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishErrorClass;
import java.io.IOException;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.util.Locale;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

/** Maps generic transport/provider outcomes to the normalized publisher contract. */
public final class ProviderErrorMapper {

  /**
   * Describes retry safety before submission and uncertainty after a request may have been sent.
   */
  public record Classification(
      PublishErrorClass errorClass,
      boolean safeToRetryBeforeSubmission,
      boolean uncertainAfterSubmission) {}

  public Classification classify(int httpStatus) {
    return classify(httpStatus, null);
  }

  /**
   * Classifies an HTTP response using status and optional generic error vocabulary only. Provider
   * endpoint names and response schemas deliberately do not appear here.
   */
  public Classification classify(int httpStatus, String errorCode) {
    PublishErrorClass codeClassification = classifyGenericCode(errorCode);
    if (codeClassification != null) {
      return classificationFor(codeClassification);
    }

    if (httpStatus == 401) {
      return new Classification(PublishErrorClass.AUTHENTICATION, false, false);
    }
    if (httpStatus == 403) {
      return new Classification(PublishErrorClass.AUTHORIZATION, false, false);
    }
    if (httpStatus == 404 || httpStatus == 405 || httpStatus == 501) {
      return new Classification(PublishErrorClass.UNSUPPORTED, false, false);
    }
    if (httpStatus == 408 || (httpStatus >= 500 && httpStatus <= 599)) {
      return new Classification(PublishErrorClass.TRANSIENT, true, true);
    }
    if (httpStatus == 409) {
      return new Classification(PublishErrorClass.DUPLICATE, false, false);
    }
    if (httpStatus == 429) {
      return new Classification(PublishErrorClass.RATE_LIMITED, true, false);
    }
    if (httpStatus == 422) {
      return new Classification(PublishErrorClass.PROVIDER_REJECTED, false, false);
    }
    if (httpStatus >= 400 && httpStatus <= 499) {
      return new Classification(PublishErrorClass.VALIDATION, false, false);
    }
    return new Classification(PublishErrorClass.UNKNOWN, false, true);
  }

  /** Classifies transport failures without deciding the caller's submission phase. */
  public Classification classify(Throwable failure) {
    Throwable cause = unwrap(failure);
    if (cause instanceof InterruptedException) {
      Thread.currentThread().interrupt();
      return new Classification(PublishErrorClass.TRANSIENT, true, true);
    }
    if (cause instanceof TimeoutException
        || cause instanceof SocketTimeoutException
        || cause instanceof ConnectException
        || cause instanceof IOException) {
      return new Classification(PublishErrorClass.TRANSIENT, true, true);
    }
    return new Classification(PublishErrorClass.UNKNOWN, false, true);
  }

  private PublishErrorClass classifyGenericCode(String errorCode) {
    if (errorCode == null || errorCode.isBlank()) {
      return null;
    }
    String normalized = errorCode.toLowerCase(Locale.ROOT);
    if (normalized.contains("duplicate") || normalized.contains("already")) {
      return PublishErrorClass.DUPLICATE;
    }
    if (normalized.contains("unsupported") || normalized.contains("not_supported")) {
      return PublishErrorClass.UNSUPPORTED;
    }
    if (normalized.contains("unauthoriz") || normalized.contains("permission")) {
      return PublishErrorClass.AUTHORIZATION;
    }
    if (normalized.contains("auth")) {
      return PublishErrorClass.AUTHENTICATION;
    }
    if (normalized.contains("rate") || normalized.contains("throttl")) {
      return PublishErrorClass.RATE_LIMITED;
    }
    if (normalized.contains("invalid") || normalized.contains("validation")) {
      return PublishErrorClass.VALIDATION;
    }
    return null;
  }

  private Classification classificationFor(PublishErrorClass errorClass) {
    boolean retryable = errorClass == PublishErrorClass.RATE_LIMITED;
    return new Classification(errorClass, retryable, false);
  }

  private Throwable unwrap(Throwable failure) {
    Throwable current = failure;
    while ((current instanceof CompletionException || current instanceof ExecutionException)
        && current.getCause() != null) {
      current = current.getCause();
    }
    return current;
  }
}
