package com.pompom.creative.openart.dto;

import java.util.List;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class OpenArtImageRequest {
  private String promptText;
  private String model;
  private List<String> referenceImagePaths;
}
