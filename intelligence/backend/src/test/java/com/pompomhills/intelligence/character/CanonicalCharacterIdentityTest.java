package com.pompomhills.intelligence.character;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CanonicalCharacterIdentityTest {
  private static final Map<String, Object> KIKO = Map.of("id", "kiko-id", "name", "Kiko");
  private static final List<Map<String, Object>> REGISTRY = List.of(KIKO);

  @Test
  void acceptsSentenceInitialGenericSpeciesAfterTheCanonicalName() {
    assertThatCode(
            () ->
                CanonicalCharacterIdentity.requireStoryIdentity(
                    "Kiko presses a teddy bear inside. The bear pops back onto the rim.",
                    KIKO,
                    REGISTRY))
        .doesNotThrowAnyException();
  }

  @Test
  void stillRejectsAnUnregisteredNamedCharacter() {
    assertThatIllegalArgumentException()
        .isThrownBy(
            () ->
                CanonicalCharacterIdentity.requireStoryIdentity(
                    "Kiko watches while Zuzu bear opens the box.", KIKO, REGISTRY))
        .withMessageContaining("Zuzu");
  }
}
