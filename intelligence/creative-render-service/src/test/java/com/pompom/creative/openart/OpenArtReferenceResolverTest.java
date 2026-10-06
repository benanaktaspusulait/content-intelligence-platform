package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class OpenArtReferenceResolverTest {

  @Test
  void resolvesAllCharacterReferencesFromTheCompiledContract(@TempDir Path tempDir)
      throws Exception {
    Path kiko = tempDir.resolve("01-CHARACTERS/kiko.png");
    Path mimi = tempDir.resolve("01-CHARACTERS/mimi.png");
    Files.createDirectories(kiko.getParent());
    Files.writeString(kiko, "kiko");
    Files.writeString(mimi, "mimi");
    String contract =
        "{\"intent\":{\"characterIntent\":{\"characterRefs\":["
            + "\"01-CHARACTERS/kiko.png\",\"01-CHARACTERS/mimi.png\"]}}}";

    OpenArtReferenceResolver resolver = new OpenArtReferenceResolver(new ObjectMapper(), tempDir);

    assertThat(resolver.resolveCharacterReferences(contract))
        .containsExactly(kiko.toString(), mimi.toString());
  }

  @Test
  void preservesHttpsReferenceUrls(@TempDir Path tempDir) {
    OpenArtReferenceResolver resolver = new OpenArtReferenceResolver(new ObjectMapper(), tempDir);

    assertThat(
            resolver.resolveCharacterReferences(
                "{\"intent\":{\"characterIntent\":{\"characterRefs\":["
                    + "\"https://cdn.openart.ai/kiko.png\"]}}}"))
        .containsExactly("https://cdn.openart.ai/kiko.png");
  }
}
