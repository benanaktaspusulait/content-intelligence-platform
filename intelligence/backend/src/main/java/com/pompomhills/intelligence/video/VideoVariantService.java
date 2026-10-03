package com.pompomhills.intelligence.video;

import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VideoVariantService {
  private final VideoRepository videos;
  private final VideoVariantRepository variants;

  public VideoVariantService(VideoRepository videos, VideoVariantRepository variants) {
    this.videos = videos;
    this.variants = variants;
  }

  @Transactional
  public VideoVariantView create(
      UUID videoId,
      UUID parentVariantId,
      VideoVariantType variantType,
      String generatedPath,
      List<Object> editOperations) {
    VideoEntity video = requireVideo(videoId);
    VideoVariantEntity parentVariant =
        parentVariantId == null ? null : requireParentVariant(videoId, parentVariantId);
    VideoVariantEntity entity =
        new VideoVariantEntity(video, parentVariant, variantType, generatedPath, editOperations);
    VideoVariantEntity saved;
    try {
      saved = variants.save(entity);
    } catch (DataIntegrityViolationException error) {
      throw new DuplicateGeneratedPathException(generatedPath, error);
    }
    return map(saved);
  }

  @Transactional(readOnly = true)
  public List<VideoVariantView> list(UUID videoId) {
    requireVideo(videoId);
    return variants.findAllByVideoId(videoId).stream().map(this::map).toList();
  }

  @Transactional(readOnly = true)
  public VideoVariantView get(UUID videoId, UUID variantId) {
    requireVideo(videoId);
    VideoVariantEntity variant =
        findVariant(videoId, variantId)
            .orElseThrow(
                () ->
                    new EntityNotFoundException(
                        "Variant "
                            + variantId
                            + " does not exist or does not belong to video "
                            + videoId));
    return map(variant);
  }

  private VideoEntity requireVideo(UUID videoId) {
    return videos
        .findById(videoId)
        .orElseThrow(() -> new EntityNotFoundException("Video not found: " + videoId));
  }

  // Used by create() for the parentVariantId field: a parent variant that doesn't belong to the
  // same video is bad caller input, so this throws IllegalArgumentException (-> 400).
  private VideoVariantEntity requireParentVariant(UUID videoId, UUID parentVariantId) {
    return findVariant(videoId, parentVariantId)
        .orElseThrow(
            () ->
                new IllegalArgumentException(
                    "Variant "
                        + parentVariantId
                        + " does not exist or does not belong to video "
                        + videoId));
  }

  // Shared lookup: scoping a variant lookup to its parent video is common to both create()'s
  // parent-variant check and get(); each call site maps the "not found" case to the exception
  // type that fits its own semantics (400 vs 404) rather than sharing one exception-throwing
  // helper.
  private Optional<VideoVariantEntity> findVariant(UUID videoId, UUID variantId) {
    return variants.findByIdAndVideoId(variantId, videoId);
  }

  private VideoVariantView map(VideoVariantEntity entity) {
    return new VideoVariantView(
        entity.getId(),
        entity.getVideo().getId(),
        entity.getParentVariant() == null ? null : entity.getParentVariant().getId(),
        entity.getVariantType().name(),
        entity.getGeneratedPath(),
        entity.getEditOperations(),
        entity.getCreatedAt());
  }

  public record VideoVariantView(
      UUID id,
      UUID videoId,
      UUID parentVariantId,
      String variantType,
      String generatedPath,
      List<Object> editOperations,
      Instant createdAt) {}

  public static class DuplicateGeneratedPathException extends IllegalArgumentException {
    public DuplicateGeneratedPathException(String generatedPath, Throwable cause) {
      super("A variant with generatedPath '" + generatedPath + "' already exists", cause);
    }
  }
}
