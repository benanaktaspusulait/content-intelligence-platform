package com.pompomhills.intelligence.video.prompt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.video.VideoEntity;
import java.nio.file.Path;
import java.nio.file.Files;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.jdbc.core.simple.JdbcClient;

class VideoPromptSourceResolverTest {
  @TempDir Path root;
  private VideoEntity video(String path) throws Exception {
    Files.writeString(root.resolve(path), "fixture");
    return new VideoEntity(UUID.randomUUID(), "hash", path, path, 10000, 10, 10, 30, 1, "h264", false, null, Instant.now());
  }
  @Test void currentDiskSnapshotIsReadWithoutReplacingItWithLatestDatabaseVersion() throws Exception {
    var video = video("ışık.mp4");
    Files.writeString(root.resolve("ışık.txt"), "first text");
    var jdbc = mock(JdbcClient.class);
    var resolver = new VideoPromptSourceResolver(new PompomProperties(root, "", Set.of("mp4"), 1, 2), jdbc);
    assertThat(resolver.resolve(video).promptText()).isEqualTo("first text");
    Files.writeString(root.resolve("ışık.txt"), "changed bytes");
    assertThat(resolver.resolve(video).promptText()).isEqualTo("changed bytes");
    verifyNoInteractions(jdbc);
  }
  @Test void multipleExactSidecarsRequireSelection() throws Exception {
    var video = video("clip.mp4");
    Files.writeString(root.resolve("clip.txt"), "one");
    Files.writeString(root.resolve("clip.md"), "two");
    var resolver = new VideoPromptSourceResolver(new PompomProperties(root, "", Set.of("mp4"), 1, 2), mock(JdbcClient.class));
    assertThat(resolver.resolve(video).status()).isEqualTo(PromptSourceResolution.Status.AMBIGUOUS);
  }
}
