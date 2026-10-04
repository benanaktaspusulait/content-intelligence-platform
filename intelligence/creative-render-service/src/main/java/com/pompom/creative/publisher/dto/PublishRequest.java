package com.pompom.creative.publisher.dto;

import java.util.List;
import lombok.Builder;
import lombok.Data;

/** Generic publish request for all platforms. */
@Data
@Builder
public class PublishRequest {
  private String videoPath;
  private String platformAccountId;
  private String idempotencyKey;
  private String title;
  private String caption;
  private List<String> hashtags;
  private String thumbnailPath;
  private Boolean isPrivate;
  private String category;

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
