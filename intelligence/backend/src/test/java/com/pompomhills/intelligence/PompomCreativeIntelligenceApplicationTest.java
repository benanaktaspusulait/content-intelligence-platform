package com.pompomhills.intelligence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Arrays;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
class PompomCreativeIntelligenceApplicationTest {

  @Autowired ApplicationContext context;

  @Test
  void doesNotScanCreativeRenderControllers() {
    assertThat(
            Arrays.stream(context.getBeanDefinitionNames())
                .map(context::getType)
                .filter(Objects::nonNull)
                .map(Class::getName))
        .doesNotContain("com.pompom.creative.api.controller.RenderJobController");
  }
}
