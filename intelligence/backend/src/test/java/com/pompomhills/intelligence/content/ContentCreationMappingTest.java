package com.pompomhills.intelligence.content;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.web.bind.annotation.PostMapping;

class ContentCreationMappingTest {
  @Test
  void workspaceCreationIsReachableThroughPost() throws Exception {
    assertThat(
            ContentWorkspaceController.class
                .getMethod("create", ContentWorkspaceController.CreateContentRequest.class)
                .getAnnotation(PostMapping.class))
        .isNotNull();
  }
}
