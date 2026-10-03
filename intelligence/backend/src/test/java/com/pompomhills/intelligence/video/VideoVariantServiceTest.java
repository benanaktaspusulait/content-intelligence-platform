package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DataIntegrityViolationException;

class VideoVariantServiceTest {

  private VideoRepository videos;
  private VideoVariantRepository variants;
  private VideoVariantService service;

  @BeforeEach
  void setUp() {
    videos = mock(VideoRepository.class);
    variants = mock(VideoVariantRepository.class);
    service = new VideoVariantService(videos, variants);
  }

  private VideoEntity sampleVideo(UUID id) {
    return new VideoEntity(
        id,
        "hash-" + id,
        "test.mp4",
        "library/" + id + ".mp4",
        15000,
        1080,
        1920,
        30.0,
        0.5625,
        "h264",
        true,
        null,
        Instant.now());
  }

  @Test
  void createRejectsAVideoIdThatDoesNotExist() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(
            () ->
                service.create(
                    videoId, null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of()))
        .isInstanceOf(EntityNotFoundException.class);
  }

  @Test
  void createRejectsAParentVariantIdThatDoesNotBelongToTheSameVideo() {
    UUID videoId = UUID.randomUUID();
    UUID otherVideoId = UUID.randomUUID();
    UUID parentVariantId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    // The parent variant lookup is scoped to THIS video; it legitimately exists but under a
    // different video, so findByIdAndVideoId(parentVariantId, videoId) correctly returns empty.
    when(variants.findByIdAndVideoId(parentVariantId, videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(
            () ->
                service.create(
                    videoId,
                    parentVariantId,
                    VideoVariantType.HOOK_COLD_OPEN,
                    "library/b.mp4",
                    List.of()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining(parentVariantId.toString());
    // Only the scoped parent-variant lookup should happen - nothing else (e.g. save()) once
    // that lookup comes back empty.
    verify(variants).findByIdAndVideoId(parentVariantId, videoId);
    org.mockito.Mockito.verifyNoMoreInteractions(variants);
  }

  @Test
  void createPersistsAValidVariantAndReturnsItsView() {
    UUID videoId = UUID.randomUUID();
    VideoEntity video = sampleVideo(videoId);
    when(videos.findById(videoId)).thenReturn(Optional.of(video));
    ArgumentCaptor<VideoVariantEntity> captor = ArgumentCaptor.forClass(VideoVariantEntity.class);
    when(variants.save(captor.capture()))
        .thenAnswer(
            invocation -> {
              VideoVariantEntity entity = invocation.getArgument(0);
              java.lang.reflect.Field idField = VideoVariantEntity.class.getDeclaredField("id");
              idField.setAccessible(true);
              idField.set(entity, UUID.randomUUID());
              java.lang.reflect.Field createdAtField =
                  VideoVariantEntity.class.getDeclaredField("createdAt");
              createdAtField.setAccessible(true);
              createdAtField.set(entity, Instant.now());
              return entity;
            });

    var result =
        service.create(
            videoId, null, VideoVariantType.TRIMMED, "library/variants/trimmed.mp4", List.of());

    assertThat(result.videoId()).isEqualTo(videoId);
    assertThat(result.variantType()).isEqualTo("TRIMMED");
    assertThat(result.generatedPath()).isEqualTo("library/variants/trimmed.mp4");
    assertThat(result.parentVariantId()).isNull();
    assertThat(captor.getValue().getVideo()).isSameAs(video);
  }

  @Test
  void createTranslatesADuplicateGeneratedPathIntoADomainException() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.save(any()))
        .thenThrow(new DataIntegrityViolationException("duplicate key value"));

    assertThatThrownBy(
            () ->
                service.create(
                    videoId,
                    null,
                    VideoVariantType.ORIGINAL,
                    "library/already-taken.mp4",
                    List.of()))
        .isInstanceOf(VideoVariantService.DuplicateGeneratedPathException.class)
        .hasMessageContaining("library/already-taken.mp4");
  }

  @Test
  void listReturnsEmptyWhenNoVariantsExistForTheVideo() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.findAllByVideoId(videoId)).thenReturn(List.of());

    assertThat(service.list(videoId)).isEmpty();
  }

  @Test
  void listRejectsAVideoIdThatDoesNotExist() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.list(videoId)).isInstanceOf(EntityNotFoundException.class);
    verify(variants, org.mockito.Mockito.never()).findAllByVideoId(any());
  }

  @Test
  void getRejectsAVariantIdThatDoesNotBelongToTheRequestedVideo() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.findByIdAndVideoId(variantId, videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.get(videoId, variantId))
        .isInstanceOf(EntityNotFoundException.class);
  }
}
