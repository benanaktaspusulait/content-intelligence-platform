package com.pompom.creative.ai.dto;

import com.pompom.creative.oauth.PlatformType;
import lombok.Builder;
import lombok.Data;

/** Caption generation request. */
@Data
@Builder
public class CaptionRequest {
  private String videoTitle;
  private String videoDescription;
  private String targetAudience; // e.g., "kids 3-6 years old"
  private String contentType; // e.g., "educational", "entertainment", "story"
  private PlatformType platform;
  private String language; // "en" or "tr"
  private Integer maxLength; // Character limit
  private Integer hashtagCount; // Number of hashtags to generate
}
