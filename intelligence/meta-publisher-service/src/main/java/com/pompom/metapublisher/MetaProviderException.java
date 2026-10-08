package com.pompom.metapublisher;

import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishersupport.ProviderErrorMapper;

public final class MetaProviderException extends RuntimeException {

  private final int httpStatus;
  private final String providerCode;
  private final String providerRequestId;
  private final ProviderErrorMapper.Classification classification;

  public MetaProviderException(
      String message,
      int httpStatus,
      String providerCode,
      String providerRequestId,
      ProviderErrorMapper.Classification classification) {
    super(message);
    this.httpStatus = httpStatus;
    this.providerCode = providerCode;
    this.providerRequestId = providerRequestId;
    this.classification = classification;
  }

  public MetaProviderException(
      String message,
      String providerRequestId,
      ProviderErrorMapper.Classification classification,
      Throwable cause) {
    super(message, cause);
    this.httpStatus = 0;
    this.providerCode = null;
    this.providerRequestId = providerRequestId;
    this.classification = classification;
  }

  public int httpStatus() {
    return httpStatus;
  }

  public String providerCode() {
    return providerCode;
  }

  public String providerRequestId() {
    return providerRequestId;
  }

  public ProviderErrorMapper.Classification classification() {
    return classification;
  }

  public PublishResult toResult(String providerPostId, String providerVideoId) {
    boolean reconciliationRequired = classification.uncertainAfterSubmission();
    if (reconciliationRequired) {
      return new PublishResult(
          PublishStatus.RECONCILIATION_REQUIRED,
          providerPostId,
          providerVideoId,
          null,
          providerRequestId,
          PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
          getMessage(),
          true);
    }
    return new PublishResult(
        PublishStatus.FAILED,
        providerPostId,
        providerVideoId,
        null,
        providerRequestId,
        classification.errorClass().wireValue(),
        getMessage(),
        false);
  }
}
