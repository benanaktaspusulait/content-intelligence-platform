package com.pompom.creative.publisher.dto;

import lombok.Builder;
import lombok.Data;

/** Generic publish response from platforms. */
@Data
@Builder
public class PublishResponse {
  private String platformPostId;
  private String platformVideoId;
  private String postUrl;
  private String status;
  private String message;
  private Boolean success;

  public static PublishResponse success(String postId, String postUrl) {
    return PublishResponse.builder()
        .success(true)
        .platformPostId(postId)
        .postUrl(postUrl)
        .status("PUBLISHED")
        .message("Successfully published")
        .build();
  }

  public static PublishResponse failure(String message) {
    return PublishResponse.builder().success(false).status("FAILED").message(message).build();
  }
}
