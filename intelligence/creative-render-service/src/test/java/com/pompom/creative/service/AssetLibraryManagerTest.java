package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.openart.dto.DownloadResult;
import com.pompom.creative.repository.RenderAssetRepository;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AssetLibraryManagerTest {

  @Mock private RenderAssetRepository assetRepo;
  @Mock private MediaProbeService mediaProbeService;

  private AssetLibraryManager manager;

  @TempDir Path tempDir;

  @BeforeEach
  void setUp() {
    manager = new AssetLibraryManager(assetRepo, mediaProbeService, tempDir.toString());
  }

  @Test
  void getContentDirectory_createsDirectoryIfNotExists() {
    // Given
    Long contentId = 123L;

    // When
    Path dir = manager.getContentDirectory(contentId);

    // Then
    assertThat(dir).exists().isDirectory();
    assertThat(dir.toString()).contains("content" + File.separator + "123");
  }

  @Test
  void getContentDirectory_returnsSamePathForSameContent() {
    // Given
    Long contentId = 456L;

    // When
    Path dir1 = manager.getContentDirectory(contentId);
    Path dir2 = manager.getContentDirectory(contentId);

    // Then
    assertThat(dir1).isEqualTo(dir2);
  }

  @Test
  void getAssetPath_firstFrame_v1() {
    // Given
    Long contentId = 123L;
    RenderAsset.AssetType assetType = RenderAsset.AssetType.FIRST_FRAME;
    int version = 1;

    // When
    Path path = manager.getAssetPath(contentId, assetType, version);

    // Then
    assertThat(path.toString()).endsWith("first-frame-v1.png");
    assertThat(path.toString()).contains("content" + File.separator + "123");
  }

  @Test
  void getAssetPath_video_v3() {
    // Given
    Long contentId = 789L;
    RenderAsset.AssetType assetType = RenderAsset.AssetType.VIDEO;
    int version = 3;

    // When
    Path path = manager.getAssetPath(contentId, assetType, version);

    // Then
    assertThat(path.toString()).endsWith("render-v3.mp4");
    assertThat(path.toString()).contains("content" + File.separator + "789");
  }

  @Test
  void getNextVersion_noExistingAssets_returns1() {
    // Given
    Long contentId = 123L;
    RenderAsset.AssetType assetType = RenderAsset.AssetType.FIRST_FRAME;
    when(assetRepo.findByContentIdOrderByCreatedAtDesc(contentId))
        .thenReturn(Collections.emptyList());

    // When
    int version = manager.getNextVersion(contentId, assetType);

    // Then
    assertThat(version).isEqualTo(1);
  }

  @Test
  void getNextVersion_existingAssets_returnsIncremented() {
    // Given
    Long contentId = 123L;
    RenderAsset.AssetType assetType = RenderAsset.AssetType.FIRST_FRAME;

    RenderAsset asset1 =
        RenderAsset.builder()
            .relativePath("content/123/first-frame-v1.png")
            .assetType(RenderAsset.AssetType.FIRST_FRAME)
            .build();

    RenderAsset asset2 =
        RenderAsset.builder()
            .relativePath("content/123/first-frame-v2.png")
            .assetType(RenderAsset.AssetType.FIRST_FRAME)
            .build();

    when(assetRepo.findByContentIdOrderByCreatedAtDesc(contentId))
        .thenReturn(List.of(asset2, asset1));

    // When
    int version = manager.getNextVersion(contentId, assetType);

    // Then
    assertThat(version).isEqualTo(3);
  }

  @Test
  void getNextVersion_mixedAssetTypes_returnsCorrectVersionForType() {
    // Given
    Long contentId = 123L;
    RenderAsset.AssetType assetType = RenderAsset.AssetType.VIDEO;

    RenderAsset firstFrame =
        RenderAsset.builder()
            .relativePath("content/123/first-frame-v5.png")
            .assetType(RenderAsset.AssetType.FIRST_FRAME)
            .build();

    RenderAsset video1 =
        RenderAsset.builder()
            .relativePath("content/123/render-v1.mp4")
            .assetType(RenderAsset.AssetType.VIDEO)
            .build();

    RenderAsset video2 =
        RenderAsset.builder()
            .relativePath("content/123/render-v2.mp4")
            .assetType(RenderAsset.AssetType.VIDEO)
            .build();

    when(assetRepo.findByContentIdOrderByCreatedAtDesc(contentId))
        .thenReturn(List.of(firstFrame, video2, video1));

    // When
    int version = manager.getNextVersion(contentId, assetType);

    // Then
    assertThat(version).isEqualTo(3); // Should ignore first-frame-v5
  }

  @Test
  void recordAsset_firstFrame_createsCorrectEntity() throws Exception {
    // Given
    RenderJob job =
        RenderJob.builder()
            .contentId(123L)
            .jobType(RenderJob.JobType.FIRST_FRAME)
            .openartJobId("mock-img-test")
            .build();

    Path assetPath = tempDir.resolve("content/123/first-frame-v1.png");
    Files.createDirectories(assetPath.getParent());
    Files.createFile(assetPath);

    DownloadResult downloadResult =
        DownloadResult.builder()
            .assetPath(assetPath.toString())
            .fileSizeBytes(12345L)
            .width(1920)
            .height(1080)
            .durationMs(null) // First frame has no duration
            .codec("png")
            .build();

    when(assetRepo.save(any(RenderAsset.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    RenderAsset result = manager.recordAsset(job, downloadResult);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getRenderJob()).isEqualTo(job);
    assertThat(result.getContentId()).isEqualTo(123L);
    assertThat(result.getAssetType()).isEqualTo(RenderAsset.AssetType.FIRST_FRAME);
    assertThat(result.getRelativePath()).isEqualTo("content/123/first-frame-v1.png");
    assertThat(result.getFileSizeBytes()).isEqualTo(12345L);
    assertThat(result.getWidth()).isEqualTo(1920);
    assertThat(result.getHeight()).isEqualTo(1080);
    assertThat(result.getDurationMs()).isNull();
    assertThat(result.getCodec()).isEqualTo("png");
    assertThat(result.getIsCurrent()).isTrue();

    verify(assetRepo).save(any(RenderAsset.class));
  }

  @Test
  void recordAsset_video_createsCorrectEntity() throws Exception {
    // Given
    RenderJob job =
        RenderJob.builder()
            .contentId(789L)
            .jobType(RenderJob.JobType.VIDEO)
            .openartJobId("mock-vid-test")
            .build();

    Path assetPath = tempDir.resolve("content/789/render-v1.mp4");
    Files.createDirectories(assetPath.getParent());
    Files.createFile(assetPath);

    DownloadResult downloadResult =
        DownloadResult.builder()
            .assetPath(assetPath.toString())
            .fileSizeBytes(5678900L)
            .width(1920)
            .height(1080)
            .durationMs(15000)
            .codec("h264")
            .build();

    when(assetRepo.save(any(RenderAsset.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    RenderAsset result = manager.recordAsset(job, downloadResult);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getAssetType()).isEqualTo(RenderAsset.AssetType.VIDEO);
    assertThat(result.getRelativePath()).isEqualTo("content/789/render-v1.mp4");
    assertThat(result.getDurationMs()).isEqualTo(15000);
    assertThat(result.getCodec()).isEqualTo("h264");
    assertThat(result.getIsCurrent()).isTrue();
  }

  @Test
  void recordAsset_savesEntityToDatabase() throws Exception {
    // Given
    RenderJob job =
        RenderJob.builder()
            .contentId(123L)
            .jobType(RenderJob.JobType.FIRST_FRAME)
            .openartJobId("mock-img-test")
            .build();

    Path assetPath = tempDir.resolve("content/123/first-frame-v1.png");
    Files.createDirectories(assetPath.getParent());
    Files.createFile(assetPath);

    DownloadResult downloadResult =
        DownloadResult.builder()
            .assetPath(assetPath.toString())
            .fileSizeBytes(12345L)
            .width(1920)
            .height(1080)
            .codec("png")
            .build();

    ArgumentCaptor<RenderAsset> captor = ArgumentCaptor.forClass(RenderAsset.class);
    when(assetRepo.save(captor.capture())).thenAnswer(invocation -> invocation.getArgument(0));

    // When
    manager.recordAsset(job, downloadResult);

    // Then
    verify(assetRepo).save(any(RenderAsset.class));
    RenderAsset savedAsset = captor.getValue();
    assertThat(savedAsset.getRelativePath()).contains("content/123/first-frame-v1.png");
  }
}
