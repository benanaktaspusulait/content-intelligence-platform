package com.pompomhills.intelligence.content;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ContentPromptQueryServiceTest {
  private PromptVersionRepository promptVersions;
  private ContentPromptQueryService service;

  @BeforeEach
  void setUp() {
    promptVersions = mock(PromptVersionRepository.class);
    service = new ContentPromptQueryService(promptVersions);
  }

  @Test
  void rejectsPromptOwnedByAnotherContent() {
    when(promptVersions.findByIdAndContentId(99L, 10L)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.load(10L, 99L))
        .isInstanceOf(ContentPromptNotFoundException.class);

    verify(promptVersions).findByIdAndContentId(99L, 10L);
  }

  @Test
  void hashesUtf8PromptText() {
    ContentEntity content = mock(ContentEntity.class);
    when(content.getId()).thenReturn(10L);
    when(content.getTitle()).thenReturn("Kiko'nun Keşfi");
    when(content.getContentType()).thenReturn(ContentEntity.ContentType.EPISODE);
    when(content.getStatus()).thenReturn(ContentEntity.ContentStatus.RENDER_READY);

    PromptVersionEntity prompt = mock(PromptVersionEntity.class);
    when(prompt.getId()).thenReturn(11L);
    when(prompt.getContent()).thenReturn(content);
    when(prompt.getVersionNumber()).thenReturn(3);
    when(prompt.getRawText()).thenReturn("Pompom 🌈 İstanbul");
    when(prompt.getParsedIr()).thenReturn("{\"scene\":1}");
    when(promptVersions.findByIdAndContentId(11L, 10L)).thenReturn(Optional.of(prompt));

    ContentPromptSnapshot snapshot = service.load(10L, 11L);

    assertThat(snapshot.contractVersion()).isEqualTo("v1");
    assertThat(snapshot.contentId()).isEqualTo(10L);
    assertThat(snapshot.promptVersionId()).isEqualTo(11L);
    assertThat(snapshot.promptText()).isEqualTo("Pompom 🌈 İstanbul");
    assertThat(snapshot.promptSha256()).matches("[0-9a-f]{64}");
    assertThat(snapshot.promptSha256())
        .isEqualTo("3639cb895bc03e9335167cdceda6b6f84d7d33f85f115dbdb151e9e96ded5c1f");
  }
}
