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
    return normalizedStatus().equals("COMPLETE");
  }

  public boolean isFailed() {
    String normalized = normalizedStatus();
    return normalized.equals("FAILED") || normalized.equals("CANCELLED");
  }

  private String normalizedStatus() {
    if (status == null) {
      return "UNKNOWN";
    }
    return status.trim().toUpperCase(Locale.ROOT).replace('-', '_').replace(' ', '_');
  }
}
