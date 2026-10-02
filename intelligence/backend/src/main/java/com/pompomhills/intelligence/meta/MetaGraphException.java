package com.pompomhills.intelligence.meta;

final class MetaGraphException extends RuntimeException {
  private final int httpStatus;
  private final Integer graphCode;
  private final Integer errorSubcode;
  private final String errorType;
  private final String fbTraceId;

  MetaGraphException(
      int httpStatus,
      Integer graphCode,
      Integer errorSubcode,
      String errorType,
      String fbTraceId,
      String sanitizedMessage) {
    super(sanitizedMessage);
    this.httpStatus = httpStatus;
    this.graphCode = graphCode;
    this.errorSubcode = errorSubcode;
    this.errorType = errorType;
    this.fbTraceId = fbTraceId;
  }

  int httpStatus() {
    return httpStatus;
  }

  Integer graphCode() {
    return graphCode;
  }

  Integer errorSubcode() {
    return errorSubcode;
  }

  String errorType() {
    return errorType;
  }

  String fbTraceId() {
    return fbTraceId;
  }

  boolean isAuthenticationUnavailable() {
    return httpStatus == 401;
  }

  boolean isPermissionDenied() {
    return httpStatus == 403 || Integer.valueOf(10).equals(graphCode);
  }
}
