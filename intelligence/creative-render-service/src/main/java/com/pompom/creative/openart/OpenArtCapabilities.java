package com.pompom.creative.openart;

/** Explicit provider capabilities exposed to orchestration and UI layers. */
public record OpenArtCapabilities(
    Support imageMultipleReferences,
    Support videoSingleStartFrame,
    Support videoMultipleElementReferences,
    Support workspaceAssetDiscovery) {

  public enum Support {
    SUPPORTED,
    UNSUPPORTED,
    UNKNOWN
  }

  /** Capability matrix verified against OpenArt CLI 0.1.1. */
  public static OpenArtCapabilities cliV011() {
    return new OpenArtCapabilities(
        Support.SUPPORTED, Support.SUPPORTED, Support.UNSUPPORTED, Support.SUPPORTED);
  }
}
