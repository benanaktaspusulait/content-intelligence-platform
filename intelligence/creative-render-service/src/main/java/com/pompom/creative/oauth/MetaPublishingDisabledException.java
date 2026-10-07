package com.pompom.creative.oauth;

/** Raised whenever a Meta publication is attempted while the feature is fail-closed. */
public class MetaPublishingDisabledException extends IllegalStateException {
  public MetaPublishingDisabledException() {
    super("Facebook and Instagram publishing is disabled");
  }
}
