package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.*;

import com.pompom.creative.openart.dto.*;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CliMockOpenArtAdapterTest {

  @Test
  void generateImage_success(@TempDir Path tempDir) {
    OpenArtAdapter adapter = new CliMockOpenArtAdapter(tempDir);

    OpenArtImageRequest request =
        OpenArtImageRequest.builder()
            .promptText("Kiko on smooth ice")
            .model("image_model_v2")
            .build();

    OpenArtJobResponse response = adapter.generateImage(request);

    assertThat(response.getJobId()).isNotNull();
    assertThat(response.getStatus()).isEqualTo("QUEUED");
  }

  @Test
  void getJobStatus_completesImmediately(@TempDir Path tempDir) {
    OpenArtAdapter adapter = new CliMockOpenArtAdapter(tempDir);

    OpenArtImageRequest request =
        OpenArtImageRequest.builder().promptText("Test prompt").model("image_model_v2").build();

    OpenArtJobResponse jobResponse = adapter.generateImage(request);

    // Mock completes immediately
    OpenArtJobStatus status = adapter.getJobStatus(jobResponse.getJobId());

    assertThat(status.isComplete()).isTrue();
    assertThat(status.isFailed()).isFalse();
  }
}
