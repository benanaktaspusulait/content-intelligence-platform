package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OpenArtReferenceResolverTest {

  @Mock private OpenArtReferenceAssetRepository repository;

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
  void fallsBackToWorkspaceCatalogWhenLocalCharacterFileIsMissing(@TempDir Path tempDir) {
    OpenArtReferenceAsset workspaceAsset =
        OpenArtReferenceAsset.builder()
            .canonicalKey("kiko")
            .displayName("Kiko")
            .source(OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE)
            .mediaType("image")
            .providerAssetId("ref-kiko")
            .providerUrl("https://cdn.openart.ai/kiko.png")
            .status(OpenArtReferenceAsset.ReferenceStatus.AVAILABLE)
            .build();
    when(repository.findByCanonicalKeyIgnoreCaseOrderBySourceAsc("kiko"))
        .thenReturn(List.of(workspaceAsset));

    OpenArtReferenceResolver resolver =
        new OpenArtReferenceResolver(new ObjectMapper(), tempDir, repository);

    assertThat(
            resolver.resolveCharacterReferences(
                "{\"intent\":{\"characterIntent\":{\"characterRefs\":["
                    + "\"01-CHARACTERS/kiko.png\"]}}}"))
        .containsExactly("https://cdn.openart.ai/kiko.png");
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
