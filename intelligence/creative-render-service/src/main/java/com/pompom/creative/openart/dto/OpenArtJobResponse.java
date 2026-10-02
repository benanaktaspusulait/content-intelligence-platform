package com.pompom.creative.openart.dto;

import java.math.BigDecimal;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtJobResponse {
  private String jobId;
  private String status;
  private BigDecimal estimatedCredits;
}
