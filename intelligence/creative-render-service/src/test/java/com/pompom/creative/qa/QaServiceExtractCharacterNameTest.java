package com.pompom.creative.qa;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Focused unit test for {@link QaService#extractCharacterName(String)}.
 *
 * <p>Exercises the extraction logic directly without constructing the Spring context or injecting
 * the {@code @Value} fields, so it is independent of the (separate) QA RestClient harness.
 */
class QaServiceExtractCharacterNameTest {

  private final QaService qaService = new QaService(null, null);

  @Test
  void extractsFirstWordAsCharacterName() {
    assertThat(qaService.extractCharacterName("Kiko Episode")).isEqualTo("Kiko");
  }

  @Test
  void stripsNonAlphabeticCharactersFromFirstWord() {
    assertThat(qaService.extractCharacterName("Mimi's Adventure")).isEqualTo("Mimis");
  }

  @Test
  void returnsUnknownForNullTitle() {
    assertThat(qaService.extractCharacterName(null)).isEqualTo("Unknown");
  }

  @Test
  void returnsUnknownForEmptyTitle() {
    assertThat(qaService.extractCharacterName("")).isEqualTo("Unknown");
  }
}
