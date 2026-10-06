package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class OpenArtCapabilitiesTest {

  @Test
  void cli011MatrixMakesUnsupportedVideoElementReferencesExplicit() {
    OpenArtCapabilities capabilities = OpenArtCapabilities.cliV011();

    assertThat(capabilities.imageMultipleReferences())
        .isEqualTo(OpenArtCapabilities.Support.SUPPORTED);
    assertThat(capabilities.videoSingleStartFrame())
        .isEqualTo(OpenArtCapabilities.Support.SUPPORTED);
    assertThat(capabilities.videoMultipleElementReferences())
        .isEqualTo(OpenArtCapabilities.Support.UNSUPPORTED);
    assertThat(capabilities.workspaceAssetDiscovery())
        .isEqualTo(OpenArtCapabilities.Support.SUPPORTED);
  }
}
