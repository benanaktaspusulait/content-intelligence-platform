package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class VideoUpscaleServiceTest {

  @Test
  void runsTheConfiguredScriptAtTheTargetResolution(@TempDir Path tempDir) throws Exception {
    Path script = tempDir.resolve("upscale-fixture.sh");
    Path log = tempDir.resolve("args.log");
    Files.writeString(
        script,
        "#!/bin/sh\nprintf '%s\\n' \"$*\" > '"
            + log
            + "'\ncp \"$3\" \"$3.tmp\"\nmv \"$3.tmp\" \"$3\"\n",
        StandardCharsets.UTF_8);
    script.toFile().setExecutable(true);
    Path video = tempDir.resolve("render-v1.mp4");
    Files.writeString(video, "low-resolution-video", StandardCharsets.UTF_8);

    VideoUpscaleService service = new VideoUpscaleService(script, true, "1920x1080", 10);

    assertThat(service.upscale(video)).isEqualTo(video);
    assertThat(Files.readString(log)).contains("-r 1920x1080 " + video);
    assertThat(Files.readString(video)).isEqualTo("low-resolution-video");
  }

  @Test
  void disabledUpscalingDoesNotInvokeTheScript(@TempDir Path tempDir) throws Exception {
    Path missingScript = tempDir.resolve("missing-upscale.sh");
    Path video = tempDir.resolve("render-v1.mp4");
    Files.writeString(video, "video", StandardCharsets.UTF_8);

    VideoUpscaleService service = new VideoUpscaleService(missingScript, false, "1920x1080", 10);

    assertThat(service.upscale(video)).isEqualTo(video);
  }
}
