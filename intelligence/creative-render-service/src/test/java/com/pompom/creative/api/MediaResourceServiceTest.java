package com.pompom.creative.api;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.service.AssetLibraryManager;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;

class MediaResourceServiceTest {
  @TempDir Path tempDir;

  @Test void quarantinedAssetsAreNeverResolved() {
    var manager = mock(AssetLibraryManager.class);
    var asset = RenderAsset.builder().quarantined(true).build();
    var service = new MediaResourceService(manager);
    assertThatThrownBy(() -> service.resolve(asset)).isInstanceOf(ResponseStatusException.class);
    verify(manager).resolveStoredPath(asset);
  }

  @Test void missingFilesReturnNotFound() {
    var manager = mock(AssetLibraryManager.class);
    var asset = RenderAsset.builder().quarantined(false).build();
    when(manager.resolveStoredPath(asset)).thenReturn(tempDir.resolve("missing.mp4"));
    assertThatThrownBy(() -> new MediaResourceService(manager).resolve(asset))
        .isInstanceOf(ResponseStatusException.class);
  }
}
