package com.pompom.creative;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.api.controller.RenderJobController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest
class CreativeRenderServiceApplicationTest {

  @Autowired ApplicationContext context;

  @Test
  void startsWithCreativeBeansOnly() {
    assertThat(context.getBeansOfType(RenderJobController.class)).hasSize(1);
    assertThat(context.getBeansWithAnnotation(SpringBootApplication.class)).hasSize(1);
  }
}
