package com.pompomhills.intelligence.video.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompomhills.intelligence.common.api.GlobalExceptionHandler;
import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import com.pompomhills.intelligence.video.MediaContentService;
import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.job.AnalysisJobService;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class VideoMediaContentTest {
  @TempDir Path root;
  private MockMvc mvc;

  @BeforeEach
  void setUp() {
    var properties =
        new PompomProperties(root, "http://localhost", Set.of("mp4", "mov", "m4v"), 3, 12);
    var controller =
        new VideoController(
            Mockito.mock(VideoService.class),
            new MediaContentService(properties),
            Mockito.mock(AnalysisJobService.class),
            Mockito.mock(CreativeAnalysisRepository.class));
    mvc =
        MockMvcBuilders.standaloneSetup(controller)
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
  }

  @Test
  void streamsSupportedMediaInline() throws Exception {
    Files.createDirectories(root.resolve("library/episode"));
    Files.write(root.resolve("library/episode/video.mp4"), "0123456789".getBytes());

    mvc.perform(get("/api/v1/videos/content").param("path", "library/episode/video.mp4"))
        .andExpect(status().isOk())
        .andExpect(header().string("Accept-Ranges", "bytes"))
        .andExpect(
            header().string("Content-Disposition", org.hamcrest.Matchers.startsWith("inline")))
        .andExpect(content().bytes("0123456789".getBytes()));
  }

  @Test
  void supportsBrowserRangeRequests() throws Exception {
    Files.write(root.resolve("video.mp4"), "0123456789".getBytes());

    mvc.perform(
            get("/api/v1/videos/content").param("path", "video.mp4").header("Range", "bytes=2-5"))
        .andExpect(status().isPartialContent())
        .andExpect(header().string("Content-Range", "bytes 2-5/10"))
        .andExpect(content().bytes("2345".getBytes()));
  }

  @Test
  void rejectsTraversalOutsideTheDataRoot() throws Exception {
    mvc.perform(get("/api/v1/videos/content").param("path", "../secret.mp4"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void returnsNotFoundForMissingMedia() throws Exception {
    mvc.perform(get("/api/v1/videos/content").param("path", "missing.mp4"))
        .andExpect(status().isNotFound());
  }
}
