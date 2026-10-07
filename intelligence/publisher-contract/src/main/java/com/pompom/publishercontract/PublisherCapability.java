package com.pompom.publishercontract;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

/** Logical publication capabilities advertised by publisher services. */
public enum PublisherCapability {
  FACEBOOK_REELS("facebook_reels"),
  INSTAGRAM_REELS("instagram_reels"),
  TIKTOK_VIDEO("tiktok_video"),
  YOUTUBE_SHORTS("youtube_shorts");

  private final String wireValue;

  PublisherCapability(String wireValue) {
    this.wireValue = wireValue;
  }

  @JsonValue
  public String wireValue() {
    return wireValue;
  }

  @JsonCreator
  public static PublisherCapability fromWireValue(String wireValue) {
    return Arrays.stream(values())
        .filter(capability -> capability.wireValue.equals(wireValue))
        .findFirst()
        .orElseThrow(
            () -> new IllegalArgumentException("Unknown publisher capability: " + wireValue));
  }
}
