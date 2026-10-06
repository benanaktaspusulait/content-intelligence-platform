package com.pompom.creative.openart;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Reconciles local character sheets and the documented OpenArt workspace upload catalog. */
@Service
@RequiredArgsConstructor
public class OpenArtReferenceCatalogService {

  private final OpenArtAdapter adapter;
  private final OpenArtReferenceAssetRepository repository;

  @Transactional
  public List<OpenArtReferenceAsset> syncWorkspaceAssets() {
    return adapter.listReferenceAssets().stream().map(this::upsertWorkspaceAsset).toList();
  }

  @Transactional
  public OpenArtReferenceAsset syncLocalReference(
      String canonicalKey, String displayName, Path localPath) {
    Path normalized = localPath.toAbsolutePath().normalize();
    if (!Files.isRegularFile(normalized)) {
      throw new IllegalArgumentException("Local reference is not a regular file: " + normalized);
    }
    String key = normalizeKey(canonicalKey == null ? displayName : canonicalKey);
    OpenArtReferenceAsset asset =
        repository
            .findBySourceAndCanonicalKey(OpenArtReferenceAsset.ReferenceSource.LOCAL, key)
            .orElseGet(OpenArtReferenceAsset::new);
    asset.setCanonicalKey(key);
    asset.setDisplayName(displayName == null || displayName.isBlank() ? key : displayName);
    asset.setSource(OpenArtReferenceAsset.ReferenceSource.LOCAL);
    asset.setMediaType(mediaType(normalized));
    asset.setLocalPath(normalized.toString());
    asset.setSha256(checksum(normalized));
    asset.setStatus(OpenArtReferenceAsset.ReferenceStatus.AVAILABLE);
    return repository.save(asset);
  }

  @Transactional(readOnly = true)
  public List<OpenArtReferenceAsset> list(String canonicalKey) {
    return canonicalKey == null || canonicalKey.isBlank()
        ? repository.findAllByOrderByCanonicalKeyAscSourceAsc()
        : repository.findByCanonicalKeyIgnoreCaseOrderBySourceAsc(canonicalKey.trim());
  }

  private OpenArtReferenceAsset upsertWorkspaceAsset(OpenArtReferenceDescriptor descriptor) {
    String key = normalizeKey(descriptor.label());
    OpenArtReferenceAsset asset =
        repository
            .findBySourceAndProviderAssetId(
                OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE,
                descriptor.providerAssetId())
            .orElseGet(
                () ->
                    repository
                        .findBySourceAndCanonicalKey(
                            OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE, key)
                        .orElseGet(OpenArtReferenceAsset::new));
    asset.setCanonicalKey(key);
    asset.setDisplayName(descriptor.label());
    asset.setSource(OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE);
    asset.setMediaType(descriptor.mediaType() == null ? "image" : descriptor.mediaType());
    asset.setProviderAssetId(descriptor.providerAssetId());
    asset.setProviderUrl(descriptor.url());
    asset.setStatus(OpenArtReferenceAsset.ReferenceStatus.AVAILABLE);
    return repository.save(asset);
  }

  private String normalizeKey(String value) {
    String normalized = value == null ? "reference" : value.trim().toLowerCase(Locale.ROOT);
    int slash = Math.max(normalized.lastIndexOf('/'), normalized.lastIndexOf('\\'));
    if (slash >= 0) normalized = normalized.substring(slash + 1);
    int dot = normalized.lastIndexOf('.');
    if (dot > 0) normalized = normalized.substring(0, dot);
    return normalized.replaceAll("[^a-z0-9_-]+", "-");
  }

  private String mediaType(Path path) {
    String name = path.getFileName().toString().toLowerCase(Locale.ROOT);
    if (name.endsWith(".png") || name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image";
    if (name.endsWith(".mp4") || name.endsWith(".mov")) return "video";
    return "unknown";
  }

  private String checksum(Path path) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      try (var input = Files.newInputStream(path)) {
        byte[] buffer = new byte[8192];
        int read;
        while ((read = input.read(buffer)) >= 0) digest.update(buffer, 0, read);
      }
      return HexFormat.of().formatHex(digest.digest());
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to checksum reference asset", error);
    }
  }
}
