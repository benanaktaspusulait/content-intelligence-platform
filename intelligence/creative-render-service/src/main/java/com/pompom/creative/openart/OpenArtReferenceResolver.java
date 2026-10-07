package com.pompom.creative.openart;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Resolves character references captured in the immutable creative contract. */
@Component
public class OpenArtReferenceResolver {

  private final ObjectMapper objectMapper;
  private final Path libraryRoot;
  private final OpenArtReferenceAssetRepository catalog;

  @Autowired
  public OpenArtReferenceResolver(
      ObjectMapper objectMapper,
      @Value("${pompom.library.root:/data/library}") String libraryRoot,
      OpenArtReferenceAssetRepository catalog) {
    this(objectMapper, Path.of(libraryRoot), catalog);
  }

  OpenArtReferenceResolver(ObjectMapper objectMapper, Path libraryRoot) {
    this(objectMapper, libraryRoot, null);
  }

  OpenArtReferenceResolver(
      ObjectMapper objectMapper, Path libraryRoot, OpenArtReferenceAssetRepository catalog) {
    this.objectMapper = objectMapper;
    this.libraryRoot = libraryRoot.toAbsolutePath().normalize();
    this.catalog = catalog;
  }

  /**
   * Resolve all character sheet paths from a compiled contract. HTTPS URLs are passed through;
   * local prompt paths are preferred, with the durable OpenArt workspace catalog as fallback.
   */
  public List<String> resolveCharacterReferences(String contractJson) {
    if (contractJson == null || contractJson.isBlank()) {
      return List.of();
    }
    try {
      JsonNode root = objectMapper.readTree(contractJson);
      JsonNode refs =
          root.at("/intent/characterIntent/characterRefs").isMissingNode()
              ? root.at("/characterIntent/characterRefs")
              : root.at("/intent/characterIntent/characterRefs");
      if (!refs.isArray()) {
        return List.of();
      }

      Set<String> resolved = new LinkedHashSet<>();
      for (JsonNode reference : refs) {
        if (!reference.isTextual() || reference.asText().isBlank()) {
          continue;
        }
        resolved.add(resolveReference(reference.asText()));
      }
      return List.copyOf(resolved);
    } catch (Exception error) {
      throw new IllegalStateException("Persisted character references are invalid", error);
    }
  }

  private String resolveReference(String reference) {
    if (reference.startsWith("https://") || reference.startsWith("http://")) {
      return reference;
    }
    Path candidate = Path.of(reference);
    Path resolved =
        (candidate.isAbsolute() ? candidate : libraryRoot.resolve(candidate))
            .toAbsolutePath()
            .normalize();
    if ((candidate.isAbsolute() || resolved.startsWith(libraryRoot))
        && Files.isRegularFile(resolved)) {
      return resolved.toString();
    }

    if (catalog != null) {
      String canonicalKey = normalizeKey(reference);
      return catalog.findByCanonicalKeyIgnoreCaseOrderBySourceAsc(canonicalKey).stream()
          .filter(asset -> asset.getStatus() == OpenArtReferenceAsset.ReferenceStatus.AVAILABLE)
          .map(this::catalogReference)
          .filter(value -> value != null)
          .findFirst()
          .orElseThrow(() -> missingReference(reference, resolved));
    }
    throw missingReference(reference, resolved);
  }

  private String catalogReference(OpenArtReferenceAsset asset) {
    if (asset.getSource() == OpenArtReferenceAsset.ReferenceSource.OPENART_WORKSPACE
        && asset.getProviderUrl() != null
        && !asset.getProviderUrl().isBlank()) {
      return asset.getProviderUrl();
    }
    if (asset.getLocalPath() != null && Files.isRegularFile(Path.of(asset.getLocalPath()))) {
      return asset.getLocalPath();
    }
    return null;
  }

  private IllegalStateException missingReference(String reference, Path resolved) {
    return new IllegalStateException(
        "Character reference file not found: " + reference + " (" + resolved + ")");
  }

  private String normalizeKey(String value) {
    String normalized = value.trim().toLowerCase(Locale.ROOT);
    int slash = Math.max(normalized.lastIndexOf('/'), normalized.lastIndexOf('\\'));
    if (slash >= 0) normalized = normalized.substring(slash + 1);
    int dot = normalized.lastIndexOf('.');
    if (dot > 0) normalized = normalized.substring(0, dot);
    return normalized.replaceAll("[^a-z0-9_-]+", "-");
  }
}
