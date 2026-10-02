package com.pompom.creative.openart.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtJobStatus {
  private String jobId;
  private String status;
  private Integer progressPercent;
  private String errorMessage;

  public boolean isComplete() {
    return "COMPLETE".equals(status);
  }

  public boolean isFailed() {
    return "FAILED".equals(status);
  }
}
