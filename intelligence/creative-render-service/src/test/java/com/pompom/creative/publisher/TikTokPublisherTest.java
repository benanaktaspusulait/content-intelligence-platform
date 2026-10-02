package com.pompom.creative.publisher;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.service.CredentialManager;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class TikTokPublisherTest {

  @Mock private CredentialManager credentialManager;

  @Mock private RestClient.Builder restClientBuilder;

  @Mock private ObjectMapper objectMapper;

  @InjectMocks private TikTokPublisher tikTokPublisher;

  @BeforeEach
  void setUp() {
    // Mock real ObjectMapper for tests
    tikTokPublisher =
        new TikTokPublisher(credentialManager, RestClient.builder(), new ObjectMapper());
  }

  @Test
  void getPlatformName_returnsTikTok() {
    // When
    String platformName = tikTokPublisher.getPlatformName();

    // Then
    assertThat(platformName).isEqualTo("TikTok");
  }

  @Test
  void isConfigured_withCredential_returnsTrue() {
    // Given
    when(credentialManager.isConnected(PlatformType.TIKTOK)).thenReturn(true);

    // When
    boolean configured = tikTokPublisher.isConfigured();

    // Then
    assertThat(configured).isTrue();
  }

  @Test
  void isConfigured_withoutCredential_returnsFalse() {
    // Given
    when(credentialManager.isConnected(PlatformType.TIKTOK)).thenReturn(false);

    // When
    boolean configured = tikTokPublisher.isConfigured();

    // Then
    assertThat(configured).isFalse();
  }

  @Test
  void publish_withoutCredential_returnsFailure() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .videoPath("/tmp/video.mp4")
            .caption("Test video")
            .hashtags(List.of("pompomhills", "kids"))
            .build();

    when(credentialManager.getActiveAccessToken(eq(PlatformType.TIKTOK)))
        .thenThrow(new RuntimeException("No credential found"));

    // When
    PublishResponse response = tikTokPublisher.publish(request);

    // Then
    assertThat(response.getSuccess()).isFalse();
    assertThat(response.getMessage()).contains("TikTok publish failed");
  }

  @Test
  void publishRequest_getFullCaption_includesHashtags() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .caption("Check out this amazing video!")
            .hashtags(List.of("pompomhills", "educational", "kids"))
            .build();

    // When
    String fullCaption = request.getFullCaption();

    // Then
    assertThat(fullCaption).contains("Check out this amazing video!");
    assertThat(fullCaption).contains("#pompomhills");
    assertThat(fullCaption).contains("#educational");
    assertThat(fullCaption).contains("#kids");
  }

  @Test
  void publishRequest_getFullCaption_handlesHashtagsWithoutHash() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .caption("Video caption")
            .hashtags(List.of("tag1", "#tag2"))
            .build();

    // When
    String fullCaption = request.getFullCaption();

    // Then
    assertThat(fullCaption).contains("#tag1");
    assertThat(fullCaption).contains("#tag2");
    assertThat(fullCaption).doesNotContain("##tag2"); // No double hash
  }

  @Test
  void publishResponse_success_createSuccessResponse() {
    // When
    PublishResponse response = PublishResponse.success("post-123", "https://tiktok.com/video/123");

    // Then
    assertThat(response.getSuccess()).isTrue();
    assertThat(response.getPlatformPostId()).isEqualTo("post-123");
    assertThat(response.getPostUrl()).isEqualTo("https://tiktok.com/video/123");
    assertThat(response.getStatus()).isEqualTo("PUBLISHED");
  }

  @Test
  void publishResponse_failure_createFailureResponse() {
    // When
    PublishResponse response = PublishResponse.failure("Upload failed: Network error");

    // Then
    assertThat(response.getSuccess()).isFalse();
    assertThat(response.getStatus()).isEqualTo("FAILED");
    assertThat(response.getMessage()).contains("Upload failed");
  }
}
