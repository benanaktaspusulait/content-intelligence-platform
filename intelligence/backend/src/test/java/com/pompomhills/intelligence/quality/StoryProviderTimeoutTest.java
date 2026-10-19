package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import java.time.Duration;
import java.util.Map;
import org.junit.jupiter.api.Test;

class StoryProviderTimeoutTest {
  @Test
  void nativeOpenaiStoryKeepsReceiptMarginWhileDefaultIsUnchanged() throws Exception {
    var method = QualityMlClient.class.getDeclaredMethod("workflowTimeout", String.class, Map.class);
    method.setAccessible(true);
    assertThat(method.invoke(null, "creative-role", Map.of("role", "STORY", "context", Map.of("storyProvider", "OPENAI"))))
        .isEqualTo(Duration.ofSeconds(75));
    assertThat(method.invoke(null, "creative-role", Map.of("role", "STORY")))
        .isEqualTo(Duration.ofSeconds(25));
    assertThat(method.invoke(null, "creative-role", Map.of("role", "BUILD_PROMPT", "context", Map.of("storyProvider", "OPENAI"))))
        .isEqualTo(Duration.ofSeconds(25));
  }
}
