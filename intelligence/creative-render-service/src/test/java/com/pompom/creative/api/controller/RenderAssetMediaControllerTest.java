package com.pompom.creative.api.controller;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.service.AssetLibraryManager;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

@ExtendWith(MockitoExtension.class)
class RenderAssetMediaControllerTest {

  @Mock private RenderAssetRepository assetRepository;
  @Mock private AssetLibraryManager assetLibraryManager;

  @TempDir Path tempDir;

  private MockMvc mvc;
  private RenderAsset asset;
  private Path media;

  @BeforeEach
  void setUp() throws Exception {
    asset = RenderAsset.builder().id(UUID.randomUUID()).assetType(RenderAsset.AssetType.VIDEO).build();
    media = tempDir.resolve("render-v1.mp4");
    Files.writeString(media, "0123456789", StandardCharsets.UTF_8);
    when(assetRepository.findById(asset.getId())).thenReturn(Optional.of(asset));
    when(assetLibraryManager.resolveStoredPath(asset)).thenReturn(media);
    mvc =
        MockMvcBuilders.standaloneSetup(
                new RenderAssetController(assetRepository, null, assetLibraryManager))
            .build();
  }

  @Test
  void streamsFullMediaInline() throws Exception {
    mvc.perform(get("/api/v1/render-assets/{id}/media", asset.getId()))
        .andExpect(status().isOk())
        .andExpect(header().string("Accept-Ranges", "bytes"));
  }

  @Test
  void streamsAByteRangeForBrowserSeeking() throws Exception {
    mvc.perform(
            get("/api/v1/render-assets/{id}/media", asset.getId())
                .header("Range", "bytes=2-5"))
        .andExpect(status().isPartialContent())
        .andExpect(header().string("Content-Range", "bytes 2-5/10"));
  }

  @Test
  void downloadsMediaAsAnAttachment() throws Exception {
    mvc.perform(get("/api/v1/render-assets/{id}/download", asset.getId()))
        .andExpect(status().isOk())
        .andExpect(header().string("Content-Disposition", org.hamcrest.Matchers.containsString("attachment")));
  }
}
