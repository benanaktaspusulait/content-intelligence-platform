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
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class MetaPublishersTest {

  @Mock private CredentialManager credentialManager;

  private FacebookPublisher facebookPublisher;
  private InstagramReelsPublisher instagramReelsPublisher;

  @BeforeEach
  void setUp() {
    facebookPublisher =
        new FacebookPublisher(credentialManager, RestClient.builder(), new ObjectMapper());

    instagramReelsPublisher =
        new InstagramReelsPublisher(credentialManager, RestClient.builder(), new ObjectMapper());
  }

  // Facebook Tests

  @Test
  void facebookPublisher_getPlatformName_returnsFacebook() {
    // When
    String platformName = facebookPublisher.getPlatformName();

    // Then
    assertThat(platformName).isEqualTo("Facebook");
  }

  @Test
  void facebookPublisher_isConfigured_withCredential_returnsTrue() {
    // Given
    when(credentialManager.isConnected(PlatformType.FACEBOOK)).thenReturn(true);

    // When
    boolean configured = facebookPublisher.isConfigured();

    // Then
    assertThat(configured).isTrue();
  }

  @Test
  void facebookPublisher_isConfigured_withoutCredential_returnsFalse() {
    // Given
    when(credentialManager.isConnected(PlatformType.FACEBOOK)).thenReturn(false);

    // When
    boolean configured = facebookPublisher.isConfigured();

    // Then
    assertThat(configured).isFalse();
  }

  @Test
  void facebookPublisher_publish_withoutCredential_returnsFailure() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .videoPath("/tmp/video.mp4")
            .title("Pompom Hills Video")
            .caption("Educational content")
            .hashtags(List.of("pompomhills", "kids"))
            .build();

    when(credentialManager.getActiveAccessToken(eq(PlatformType.FACEBOOK)))
        .thenThrow(new RuntimeException("No credential found"));

    // When
    PublishResponse response = facebookPublisher.publish(request);

    // Then
    assertThat(response.getSuccess()).isFalse();
    assertThat(response.getMessage()).contains("Facebook publish failed");
  }

  // Instagram Tests

  @Test
  void instagramPublisher_getPlatformName_returnsInstagramReels() {
    // When
    String platformName = instagramReelsPublisher.getPlatformName();

    // Then
    assertThat(platformName).isEqualTo("Instagram Reels");
  }

  @Test
  void instagramPublisher_isConfigured_withCredential_returnsTrue() {
    // Given
    when(credentialManager.isConnected(PlatformType.INSTAGRAM)).thenReturn(true);

    // When
    boolean configured = instagramReelsPublisher.isConfigured();

    // Then
    assertThat(configured).isTrue();
  }

  @Test
  void instagramPublisher_isConfigured_withoutCredential_returnsFalse() {
    // Given
    when(credentialManager.isConnected(PlatformType.INSTAGRAM)).thenReturn(false);

    // When
    boolean configured = instagramReelsPublisher.isConfigured();

    // Then
    assertThat(configured).isFalse();
  }

  @Test
  void instagramPublisher_publish_withoutCredential_returnsFailure() {
    // Given
    PublishRequest request =
        PublishRequest.builder()
            .videoPath("/tmp/video.mp4")
            .caption("Check out this Reel!")
            .hashtags(List.of("pompomhills", "reels", "kids"))
            .build();

    when(credentialManager.getActiveAccessToken(eq(PlatformType.INSTAGRAM)))
        .thenThrow(new RuntimeException("No credential found"));

    // When
    PublishResponse response = instagramReelsPublisher.publish(request);

    // Then
    assertThat(response.getSuccess()).isFalse();
    assertThat(response.getMessage()).contains("Instagram Reels publish failed");
  }
}
