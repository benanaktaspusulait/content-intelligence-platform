package com.pompom.creative.ai;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.ai.dto.CaptionRequest;
import com.pompom.creative.ai.dto.CaptionResponse;
import com.pompom.creative.oauth.PlatformType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class CaptionGeneratorServiceTest {

  private CaptionGeneratorService captionGeneratorService;

  @BeforeEach
  void setUp() {
    captionGeneratorService = new CaptionGeneratorService(RestClient.builder(), new ObjectMapper());

    // Disable AI for fallback testing
    ReflectionTestUtils.setField(captionGeneratorService, "aiEnabled", false);
  }

  @Test
  void generateCaption_fallbackMode_generatesCaptionWithHashtags() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Learn Colors with Pompom")
            .videoDescription("Educational video about colors for toddlers")
            .targetAudience("kids 3-6 years old")
            .contentType("educational")
            .platform(PlatformType.TIKTOK)
            .language("en")
            .maxLength(500)
            .hashtagCount(5)
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response).isNotNull();
    assertThat(response.getCaption()).contains("Learn Colors with Pompom");
    assertThat(response.getHashtags()).isNotEmpty();
    assertThat(response.getPlatform()).isEqualTo("TIKTOK");
    assertThat(response.getLanguage()).isEqualTo("en");
  }

  @Test
  void generateCaption_tiktokPlatform_usesTikTokHashtags() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Test Video")
            .platform(PlatformType.TIKTOK)
            .language("en")
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response.getHashtags()).contains("pompomhills");
    assertThat(response.getHashtags())
        .anyMatch(tag -> tag.contains("tiktok") || tag.contains("kidstiktok"));
  }

  @Test
  void generateCaption_youtubePlatform_usesYouTubeHashtags() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Test Video")
            .platform(PlatformType.YOUTUBE)
            .language("en")
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response.getHashtags()).contains("pompomhills");
    assertThat(response.getHashtags()).contains("shorts");
  }

  @Test
  void generateCaption_facebookPlatform_usesFacebookHashtags() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Test Video")
            .platform(PlatformType.FACEBOOK)
            .language("en")
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response.getHashtags()).contains("pompomhills");
    assertThat(response.getHashtags())
        .anyMatch(tag -> tag.contains("kids") || tag.contains("educational"));
  }

  @Test
  void generateCaption_instagramPlatform_usesInstagramHashtags() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Test Video")
            .platform(PlatformType.INSTAGRAM)
            .language("en")
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response.getHashtags()).contains("pompomhills");
    assertThat(response.getHashtags()).contains("reels");
  }

  @Test
  void captionResponse_getFullCaption_combinesCaptionAndHashtags() {
    // Given
    CaptionResponse response =
        CaptionResponse.builder()
            .caption("Check out this amazing video!")
            .hashtags(java.util.List.of("pompomhills", "educational", "kids"))
            .build();

    // When
    String fullCaption = response.getFullCaption();

    // Then
    assertThat(fullCaption).contains("Check out this amazing video!");
    assertThat(fullCaption).contains("#pompomhills");
    assertThat(fullCaption).contains("#educational");
    assertThat(fullCaption).contains("#kids");
  }

  @Test
  void captionResponse_getFullCaption_handlesHashtagsWithoutHash() {
    // Given
    CaptionResponse response =
        CaptionResponse.builder()
            .caption("Video caption")
            .hashtags(java.util.List.of("tag1", "#tag2"))
            .build();

    // When
    String fullCaption = response.getFullCaption();

    // Then
    assertThat(fullCaption).contains("#tag1");
    assertThat(fullCaption).contains("#tag2");
    assertThat(fullCaption).doesNotContain("##tag2"); // No double hash
  }

  @Test
  void isConfigured_aiDisabled_returnsFalse() {
    // Given: AI is disabled in setUp

    // When
    boolean configured = captionGeneratorService.isConfigured();

    // Then
    assertThat(configured).isFalse();
  }

  @Test
  void isConfigured_aiEnabledWithKey_returnsTrue() {
    // Given
    ReflectionTestUtils.setField(captionGeneratorService, "aiEnabled", true);
    ReflectionTestUtils.setField(captionGeneratorService, "openaiApiKey", "test-api-key");

    // When
    boolean configured = captionGeneratorService.isConfigured();

    // Then
    assertThat(configured).isTrue();
  }

  @Test
  void generateCaption_withDescription_includesDescription() {
    // Given
    CaptionRequest request =
        CaptionRequest.builder()
            .videoTitle("Colors Video")
            .videoDescription("Learn red, blue, and yellow")
            .platform(PlatformType.YOUTUBE)
            .language("en")
            .build();

    // When
    CaptionResponse response = captionGeneratorService.generateCaption(request);

    // Then
    assertThat(response.getCaption()).contains("Colors Video");
    assertThat(response.getCaption()).contains("Learn red, blue, and yellow");
  }
}
