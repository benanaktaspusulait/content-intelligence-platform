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
class YouTubeShortsPublisherTest {

  @Mock private CredentialManager credentialManager;

  @Mock private RestClient.Builder restClientBuilder;

  @Mock private ObjectMapper objectMapper;

  @InjectMocks private YouTubeShortsPublisher youTubeShortsPublisher;

  @BeforeEach
  void setUp() {
    // Mock real ObjectMapper for tests
    youTubeShortsPublisher =
        new YouTubeShortsPublisher(credentialManager, RestClient.builder(), new ObjectMapper());
  }

  @Test
  void getPlatformName_returnsYouTubeShorts() {
    // When
    String platformName = youTubeShortsPublisher.getPlatformName();

    // Then
    assertThat(platformName).isEqualTo("YouTube Shorts");
  }

  @Test
  void isConfigured_withCredential_returnsTrue() {
    // Given
    when(credentialManager.isConnected(PlatformType.YOUTUBE)).thenReturn(true);

    // When
    boolean configured = youTubeShortsPublisher.isConfigured();

    // Then
    assertThat(configured).isTrue();
  }

  @Test
  void isConfigured_withoutCredential_returnsFalse() {
    // Given
    when(credentialManager.isConnected(PlatformType.YOUTUBE)).thenReturn(false);

    // When
    boolean configured = youTubeShortsPublisher.isConfigured();

    // Then
    assertThat(configured).isFalse();
  }

  @Test
  void publish_withoutCredential_returnsFailure() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .videoPath("/tmp/video.mp4")
            .title("Pompom Hills Fun")
            .caption("Educational video for kids")
            .hashtags(List.of("pompomhills", "kids", "educational"))
            .build();

    when(credentialManager.getActiveAccessToken(eq(PlatformType.YOUTUBE)))
        .thenThrow(new RuntimeException("No credential found"));

    // When
    PublishResponse response = youTubeShortsPublisher.publish(request);

    // Then
    assertThat(response.getSuccess()).isFalse();
    assertThat(response.getMessage()).contains("YouTube Shorts publish failed");
  }
}
