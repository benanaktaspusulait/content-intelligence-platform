package com.pompom.creative.openart.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class DownloadResult {
  private String assetPath;
  private Long fileSizeBytes;
  private Integer width;
  private Integer height;
  private Integer durationMs;
  private String codec;
}
