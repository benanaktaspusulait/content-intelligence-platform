package com.pompom.creative.openart;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class OpenArtReferenceCatalogServiceTest {

  @Mock private OpenArtAdapter adapter;
  @Mock private OpenArtReferenceAssetRepository repository;

  @Test
  void syncWorkspaceAssetsPersistsProviderIdentityAndCanonicalKey() {
    when(adapter.listReferenceAssets())
        .thenReturn(
            List.of(
                new OpenArtReferenceDescriptor(
                    "ref-1", "https://cdn.openart.ai/kiko.png", "Kiko.png", "image")));
    when(repository.findBySourceAndCanonicalKey(
            OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE, "kiko"))
        .thenReturn(Optional.empty());
    when(repository.save(any(OpenArtReferenceAsset.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    OpenArtReferenceCatalogService service =
        new OpenArtReferenceCatalogService(adapter, repository);

    List<OpenArtReferenceAsset> result = service.syncWorkspaceAssets();

    assertThat(result)
        .singleElement()
        .satisfies(
            asset -> {
              assertThat(asset.getSource())
                  .isEqualTo(OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE);
              assertThat(asset.getCanonicalKey()).isEqualTo("kiko");
              assertThat(asset.getProviderAssetId()).isEqualTo("ref-1");
              assertThat(asset.getProviderUrl()).isEqualTo("https://cdn.openart.ai/kiko.png");
              assertThat(asset.getStatus())
                  .isEqualTo(OpenArtReferenceAsset.ReferenceStatus.AVAILABLE);
            });
  }

  @Test
  void syncLocalReferenceStoresChecksumAndLocalSource(@TempDir Path tempDir) throws Exception {
    Path reference = tempDir.resolve("01-CHARACTERS/mimi.png");
    Files.createDirectories(reference.getParent());
    Files.writeString(reference, "mimi-reference");
    when(repository.findBySourceAndCanonicalKey(
            OpenArtReferenceAsset.ReferenceSource.LOCAL, "mimi"))
        .thenReturn(Optional.empty());
    when(repository.save(any(OpenArtReferenceAsset.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    OpenArtReferenceCatalogService service =
        new OpenArtReferenceCatalogService(adapter, repository);

    OpenArtReferenceAsset result = service.syncLocalReference("mimi", "Mimi", reference);

    assertThat(result.getSource()).isEqualTo(OpenArtReferenceAsset.ReferenceSource.LOCAL);
    assertThat(result.getCanonicalKey()).isEqualTo("mimi");
    assertThat(result.getLocalPath()).isEqualTo(reference.toAbsolutePath().normalize().toString());
    assertThat(result.getSha256()).hasSize(64);
    assertThat(result.getStatus()).isEqualTo(OpenArtReferenceAsset.ReferenceStatus.AVAILABLE);
  }
}
