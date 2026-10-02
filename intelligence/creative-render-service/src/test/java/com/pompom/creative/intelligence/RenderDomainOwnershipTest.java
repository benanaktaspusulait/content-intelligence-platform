package com.pompom.creative.intelligence;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.creative.domain.OpenArtCreditLog;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.domain.RenderQaResult;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

/**
 * Guards the service boundary: render-side entities own content/prompt data only by scalar id plus
 * immutable snapshots. The legacy {@code Content}/{@code PromptVersion} JPA types no longer exist
 * in this module, so the invariant is expressed against the forbidden type simple names.
 */
class RenderDomainOwnershipTest {
  @Test
  void renderJobStoresScalarOwnershipAndImmutablePromptSnapshot() throws Exception {
    assertThat(RenderJob.class.getDeclaredField("contentId").getType()).isEqualTo(Long.class);
    assertThat(RenderJob.class.getDeclaredField("promptVersionId").getType()).isEqualTo(Long.class);
    assertThat(RenderJob.class.getDeclaredField("contentTitleSnapshot").getType())
        .isEqualTo(String.class);
    assertThat(RenderJob.class.getDeclaredField("promptVersionNumberSnapshot").getType())
        .isEqualTo(Integer.class);
    assertThat(RenderJob.class.getDeclaredField("promptSha256").getType()).isEqualTo(String.class);
    assertThat(RenderJob.class.getDeclaredField("promptTextSnapshot").getType())
        .isEqualTo(String.class);

    assertNoFieldTypedByName(RenderJob.class, "Content", "PromptVersion");
  }

  @Test
  void renderJobExposesNoPublicSettersForImmutableSnapshotFields() {
    assertNoPublicSetter(
        RenderJob.class,
        "setContentId",
        "setPromptVersionId",
        "setContentTitleSnapshot",
        "setPromptVersionNumberSnapshot",
        "setPromptSha256",
        "setPromptTextSnapshot");
  }

  @Test
  void dependentRenderEntitiesStoreOnlyScalarForeignOwnership() throws Exception {
    assertThat(RenderAsset.class.getDeclaredField("contentId").getType()).isEqualTo(Long.class);
    assertThat(RenderQaResult.class.getDeclaredField("promptVersionId").getType())
        .isEqualTo(Long.class);
    assertThat(OpenArtCreditLog.class.getDeclaredField("promptVersionId").getType())
        .isEqualTo(Long.class);

    assertNoFieldTypedByName(RenderAsset.class, "Content");
    assertNoFieldTypedByName(RenderQaResult.class, "PromptVersion");
    assertNoFieldTypedByName(OpenArtCreditLog.class, "PromptVersion");
  }

  private static void assertNoFieldTypedByName(Class<?> owner, String... forbiddenSimpleNames) {
    assertThat(
            Arrays.stream(owner.getDeclaredFields()).map(Field::getType).map(Class::getSimpleName))
        .doesNotContain(forbiddenSimpleNames);
  }

  private static void assertNoPublicSetter(Class<?> owner, String... forbiddenSetterNames) {
    assertThat(Arrays.stream(owner.getMethods()).map(Method::getName))
        .doesNotContain(forbiddenSetterNames);
  }
}
