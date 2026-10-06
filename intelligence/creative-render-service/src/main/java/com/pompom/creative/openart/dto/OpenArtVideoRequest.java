package com.pompom.creative.openart.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtVideoRequest {
  private String promptText;
  private String model;
  private String firstFrameImageId;
  private Integer durationSeconds;
  private String aspectRatio;
  private String resolution;
}
