package com.pompom.creative.ai.dto;

import java.util.List;
import lombok.Builder;
import lombok.Data;

/** Caption generation response. */
@Data
@Builder
public class CaptionResponse {
  private String caption;
  private List<String> hashtags;
  private String platform;
  private String language;
  private Integer characterCount;
  private Boolean withinLimit;

  public String getFullCaption() {
    if (hashtags == null || hashtags.isEmpty()) {
      return caption;
    }

    StringBuilder sb = new StringBuilder(caption);
    if (!caption.isEmpty() && !caption.endsWith("\n")) {
      sb.append("\n\n");
    }

    for (String hashtag : hashtags) {
      if (!hashtag.startsWith("#")) {
        sb.append("#");
      }
      sb.append(hashtag).append(" ");
    }

    return sb.toString().trim();
  }
}
