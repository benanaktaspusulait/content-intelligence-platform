package com.pompom.creative.openart;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Resolves character references captured in the immutable creative contract. */
@Component
public class OpenArtReferenceResolver {

  private final ObjectMapper objectMapper;
  private final Path libraryRoot;

  @Autowired
  public OpenArtReferenceResolver(
      ObjectMapper objectMapper,
      @Value("${pompom.library.root:/data/library}") String libraryRoot) {
    this(objectMapper, Path.of(libraryRoot));
  }

  OpenArtReferenceResolver(ObjectMapper objectMapper, Path libraryRoot) {
    this.objectMapper = objectMapper;
    this.libraryRoot = libraryRoot.toAbsolutePath().normalize();
  }

  /**
   * Resolve all character sheet paths from a compiled contract. HTTPS URLs are passed through;
   * relative prompt paths are resolved under the read-only production library mount.
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
    if (!resolved.startsWith(libraryRoot) && !candidate.isAbsolute()) {
      throw new IllegalArgumentException(
          "Character reference escapes the library root: " + reference);
    }
    if (!Files.isRegularFile(resolved)) {
      throw new IllegalStateException("Character reference file not found: " + resolved);
    }
    return resolved.toString();
  }
}
