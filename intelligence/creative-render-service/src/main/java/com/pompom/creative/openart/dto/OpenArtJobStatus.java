package com.pompom.creative.openart.dto;

import java.util.Locale;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtJobStatus {
  private String jobId;
  private String status;
  private Integer progressPercent;
  private String errorMessage;
  private java.math.BigDecimal creditsUsed;

  public boolean isComplete() {
    return switch (normalizedStatus()) {
      case "COMPLETE", "COMPLETED", "SUCCEEDED", "SUCCESS", "DONE" -> true;
      default -> false;
    };
  }

  public boolean isFailed() {
    return switch (normalizedStatus()) {
      case "FAILED", "FAILURE", "ERROR", "ERRORED", "EXPIRED", "CANCELLED", "CANCELED" -> true;
      default -> false;
    };
  }

  private String normalizedStatus() {
    if (status == null) {
      return "UNKNOWN";
    }
    return status.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
  }
}
