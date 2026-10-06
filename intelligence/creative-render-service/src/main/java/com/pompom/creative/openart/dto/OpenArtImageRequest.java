package com.pompom.creative.openart.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtImageRequest {
  private String promptText;
  private String model;
}
