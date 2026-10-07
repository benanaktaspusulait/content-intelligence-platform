package com.pompom.publishercontract;

import jakarta.validation.constraints.NotNull;

/**
 * Provider-neutral outcome returned by an internal publisher.
 *
 * <p>The result is used by both {@code POST /internal/v1/publish} and {@code POST
 * /internal/v1/reconcile}. An accepted result is not a completed publication; uncertain provider
 * state is represented by {@link PublishStatus#RECONCILIATION_REQUIRED} and the explicit
 * reconciliation flag. Accepted and completed results have no error class or reconciliation flag;
 * failed results have a terminal error class without reconciliation; uncertain results use a
 * transient, unknown, or reconciliation-required error class with reconciliation required.
 */
public record PublishResult(
    @NotNull PublishStatus status,
    String providerPostId,
    String providerVideoId,
    String permalink,
    String providerRequestId,
    String errorClass,
    String message,
    boolean reconciliationRequired) {

  public PublishResult {
    errorClass =
        errorClass == null ? null : PublishErrorClass.fromWireValue(errorClass).wireValue();

    if (status != null) {
      switch (status) {
        case ACCEPTED, COMPLETED -> {
          if (errorClass != null || reconciliationRequired) {
            throw invalidLifecycle(status, errorClass, reconciliationRequired);
          }
        }
        case FAILED -> {
          if (errorClass == null || isUncertainErrorClass(errorClass) || reconciliationRequired) {
            throw invalidLifecycle(status, errorClass, reconciliationRequired);
          }
        }
        case RECONCILIATION_REQUIRED -> {
          if (!isUncertainErrorClass(errorClass) || !reconciliationRequired) {
            throw invalidLifecycle(status, errorClass, reconciliationRequired);
          }
        }
      }
    }
  }

  private static boolean isUncertainErrorClass(String errorClass) {
    return PublishErrorClass.TRANSIENT.wireValue().equals(errorClass)
        || PublishErrorClass.UNKNOWN.wireValue().equals(errorClass)
        || PublishErrorClass.RECONCILIATION_REQUIRED.wireValue().equals(errorClass);
  }

  private static IllegalArgumentException invalidLifecycle(
      PublishStatus status, String errorClass, boolean reconciliationRequired) {
    return new IllegalArgumentException(
        "Invalid publish lifecycle for "
            + status
            + ": errorClass="
            + errorClass
            + ", reconciliationRequired="
            + reconciliationRequired);
  }
}
