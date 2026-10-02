package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PlatformCredential;
import com.pompom.creative.oauth.OAuthService;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.oauth.dto.OAuthToken;
import com.pompom.creative.repository.PlatformCredentialRepository;
import com.pompom.creative.security.EncryptionService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CredentialManagerTest {

  @Mock private PlatformCredentialRepository credentialRepository;

  @Mock private EncryptionService encryptionService;

  @Mock private OAuthService oauthService;

  @InjectMocks private CredentialManager credentialManager;

  /**
   * Stubs {@link EncryptionService#encrypt} and {@link EncryptionService#decrypt} for the handful
   * of tests that actually exercise encryption. Scoped per-test (not {@code @BeforeEach}) because
   * Mockito strict stubbing flags it as {@code UnnecessaryStubbing} on every test that never calls
   * {@code encrypt}/{@code decrypt} (e.g. {@code isConnected_*}, {@code getActivePlatforms_*}).
   */
  private void stubEncryption() {
    when(encryptionService.encrypt(anyString()))
        .thenAnswer(invocation -> "ENCRYPTED_" + invocation.getArgument(0));
  }

  /** Scoped the same way as {@link #stubEncryption()}, for tests that only decrypt. */
  private void stubDecryption() {
    when(encryptionService.decrypt(anyString()))
        .thenAnswer(invocation -> invocation.getArgument(0).toString().replace("ENCRYPTED_", ""));
  }

  @Test
  void saveCredential_newPlatform_createsNewCredential() {
    stubEncryption();
    // Given
    PlatformType platform = PlatformType.TIKTOK;
    // saveCredential encrypts both access and refresh tokens.
    OAuthToken token =
        OAuthToken.builder()
            .accessToken("access-token-123")
            .refreshToken("refresh-token-456")
            .tokenType("Bearer")
            .scope("user.info.basic,video.upload")
            .expiresAt(Instant.now().plusSeconds(3600))
            .platformUserId("tiktok-user-123")
            .build();

    when(credentialRepository.findByPlatform(platform)).thenReturn(Optional.empty());
    when(credentialRepository.save(any(PlatformCredential.class)))
        .thenAnswer(
            invocation -> {
              PlatformCredential cred = invocation.getArgument(0);
              cred.setId(UUID.randomUUID());
              return cred;
            });

    // When
    PlatformCredential result = credentialManager.saveCredential(platform, token);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getPlatform()).isEqualTo(platform);
    assertThat(result.getIsActive()).isTrue();

    ArgumentCaptor<PlatformCredential> captor = ArgumentCaptor.forClass(PlatformCredential.class);
    verify(credentialRepository).save(captor.capture());

    PlatformCredential saved = captor.getValue();
    assertThat(saved.getAccessTokenEncrypted()).isEqualTo("ENCRYPTED_access-token-123");
    assertThat(saved.getRefreshTokenEncrypted()).isEqualTo("ENCRYPTED_refresh-token-456");
    assertThat(saved.getPlatformUserId()).isEqualTo("tiktok-user-123");
  }

  @Test
  void saveCredential_existingPlatform_updatesCredential() {
    stubEncryption();
    // Given
    PlatformType platform = PlatformType.YOUTUBE;
    // saveCredential encrypts both access and refresh tokens on every call.
    UUID existingId = UUID.randomUUID();

    PlatformCredential existing =
        PlatformCredential.builder()
            .id(existingId)
            .platform(platform)
            .accessTokenEncrypted("ENCRYPTED_old-token")
            .connectedAt(Instant.now().minusSeconds(3600))
            .build();

    OAuthToken newToken =
        OAuthToken.builder()
            .accessToken("new-access-token")
            .refreshToken("new-refresh-token")
            .tokenType("Bearer")
            .expiresAt(Instant.now().plusSeconds(3600))
            .build();

    when(credentialRepository.findByPlatform(platform)).thenReturn(Optional.of(existing));
    when(credentialRepository.save(any(PlatformCredential.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    PlatformCredential result = credentialManager.saveCredential(platform, newToken);

    // Then
    assertThat(result.getId()).isEqualTo(existingId);
    assertThat(result.getAccessTokenEncrypted()).isEqualTo("ENCRYPTED_new-access-token");
    assertThat(result.getRefreshTokenEncrypted()).isEqualTo("ENCRYPTED_new-refresh-token");
  }

  @Test
  void getCredential_existingActive_returnsDecryptedToken() {
    // getCredential decrypts both the stored access and refresh tokens.
    when(encryptionService.decrypt("ENCRYPTED_fb-access-token")).thenReturn("fb-access-token");
    when(encryptionService.decrypt("ENCRYPTED_fb-refresh-token")).thenReturn("fb-refresh-token");
    // Given
    PlatformType platform = PlatformType.FACEBOOK;

    PlatformCredential credential =
        PlatformCredential.builder()
            .platform(platform)
            .accessTokenEncrypted("ENCRYPTED_fb-access-token")
            .refreshTokenEncrypted("ENCRYPTED_fb-refresh-token")
            .tokenType("Bearer")
            .scope("pages_manage_posts")
            .expiresAt(Instant.now().plusSeconds(3600))
            .isActive(true)
            .build();

    when(credentialRepository.findByPlatformAndIsActiveTrue(platform))
        .thenReturn(Optional.of(credential));

    // When
    Optional<OAuthToken> result = credentialManager.getCredential(platform);

    // Then
    assertThat(result).isPresent();
    assertThat(result.get().getAccessToken()).isEqualTo("fb-access-token");
    assertThat(result.get().getRefreshToken()).isEqualTo("fb-refresh-token");
    assertThat(result.get().getTokenType()).isEqualTo("Bearer");
  }

  @Test
  void getCredential_notFound_returnsEmpty() {
    // Given
    PlatformType platform = PlatformType.INSTAGRAM;
    when(credentialRepository.findByPlatformAndIsActiveTrue(platform)).thenReturn(Optional.empty());

    // When
    Optional<OAuthToken> result = credentialManager.getCredential(platform);

    // Then
    assertThat(result).isEmpty();
  }

  @Test
  void getActiveAccessToken_validToken_returnsAccessToken() {
    // getActiveAccessToken always decrypts the stored access token before returning it.
    when(encryptionService.decrypt("ENCRYPTED_tiktok-token")).thenReturn("tiktok-token");
    // Given
    PlatformType platform = PlatformType.TIKTOK;

    PlatformCredential credential =
        PlatformCredential.builder()
            .platform(platform)
            .accessTokenEncrypted("ENCRYPTED_tiktok-token")
            .expiresAt(Instant.now().plusSeconds(3600)) // 1 hour from now
            .isActive(true)
            .build();

    when(credentialRepository.findByPlatformAndIsActiveTrue(platform))
        .thenReturn(Optional.of(credential));

    // When
    String accessToken = credentialManager.getActiveAccessToken(platform);

    // Then
    assertThat(accessToken).isEqualTo("tiktok-token");
    verify(credentialRepository, times(1)).findByPlatformAndIsActiveTrue(platform);
  }

  @Test
  void getActiveAccessToken_expiringSoon_refreshesToken() {
    // refreshIfNeeded() decrypts the stored refresh token, then saveCredential() (called from
    // refreshIfNeeded) encrypts the new access/refresh tokens.
    stubEncryption();
    stubDecryption();
    // Given
    PlatformType platform = PlatformType.YOUTUBE;

    PlatformCredential credential =
        PlatformCredential.builder()
            .platform(platform)
            .accessTokenEncrypted("ENCRYPTED_old-token")
            .refreshTokenEncrypted("ENCRYPTED_refresh-token")
            .expiresAt(Instant.now().plusSeconds(200)) // Expires in 200s (< 5 min)
            .isActive(true)
            .build();

    OAuthToken newToken =
        OAuthToken.builder()
            .accessToken("new-token")
            .refreshToken("refresh-token")
            .expiresAt(Instant.now().plusSeconds(3600))
            .build();

    when(credentialRepository.findByPlatformAndIsActiveTrue(platform))
        .thenReturn(Optional.of(credential))
        .thenReturn(Optional.of(credential)); // Second call after refresh

    when(oauthService.refreshAccessToken(eq(platform), anyString())).thenReturn(newToken);

    when(credentialRepository.save(any(PlatformCredential.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    String accessToken = credentialManager.getActiveAccessToken(platform);

    // Then
    assertThat(accessToken).isNotNull();
    verify(oauthService).refreshAccessToken(eq(platform), eq("refresh-token"));
    verify(credentialRepository, atLeast(2)).findByPlatformAndIsActiveTrue(platform);
  }

  @Test
  void refreshIfNeeded_tokenValid_doesNotRefresh() {
    // Token is not expiring, so refreshIfNeeded returns false before ever touching
    // EncryptionService; no stub needed.
    // Given
    PlatformType platform = PlatformType.TIKTOK;

    PlatformCredential credential =
        PlatformCredential.builder()
            .platform(platform)
            .accessTokenEncrypted("ENCRYPTED_token")
            .expiresAt(Instant.now().plusSeconds(3600)) // 1 hour from now
            .isActive(true)
            .build();

    when(credentialRepository.findByPlatformAndIsActiveTrue(platform))
        .thenReturn(Optional.of(credential));

    // When
    boolean refreshed = credentialManager.refreshIfNeeded(platform);

    // Then
    assertThat(refreshed).isFalse();
    verify(oauthService, never()).refreshAccessToken(any(), any());
  }

  @Test
  void disconnectPlatform_existingPlatform_marksInactive() {
    // disconnectPlatform only flips isActive; it never touches EncryptionService.
    // Given
    PlatformType platform = PlatformType.FACEBOOK;

    PlatformCredential credential =
        PlatformCredential.builder()
            .id(UUID.randomUUID())
            .platform(platform)
            .isActive(true)
            .build();

    when(credentialRepository.findByPlatform(platform)).thenReturn(Optional.of(credential));
    when(credentialRepository.save(any(PlatformCredential.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    credentialManager.disconnectPlatform(platform);

    // Then
    ArgumentCaptor<PlatformCredential> captor = ArgumentCaptor.forClass(PlatformCredential.class);
    verify(credentialRepository).save(captor.capture());
    assertThat(captor.getValue().getIsActive()).isFalse();
  }

  @Test
  void getActivePlatforms_multipleActive_returnsAllActive() {
    // Given
    List<PlatformCredential> activeCredentials =
        List.of(
            PlatformCredential.builder().platform(PlatformType.TIKTOK).isActive(true).build(),
            PlatformCredential.builder().platform(PlatformType.YOUTUBE).isActive(true).build());

    when(credentialRepository.findByIsActiveTrue()).thenReturn(activeCredentials);

    // When
    List<PlatformType> result = credentialManager.getActivePlatforms();

    // Then
    assertThat(result).hasSize(2);
    assertThat(result).contains(PlatformType.TIKTOK, PlatformType.YOUTUBE);
  }

  @Test
  void isConnected_activeCredential_returnsTrue() {
    // Given
    PlatformType platform = PlatformType.INSTAGRAM;
    when(credentialRepository.existsByPlatformAndIsActiveTrue(platform)).thenReturn(true);

    // When
    boolean connected = credentialManager.isConnected(platform);

    // Then
    assertThat(connected).isTrue();
  }

  @Test
  void isConnected_noCredential_returnsFalse() {
    // Given
    PlatformType platform = PlatformType.FACEBOOK;
    when(credentialRepository.existsByPlatformAndIsActiveTrue(platform)).thenReturn(false);

    // When
    boolean connected = credentialManager.isConnected(platform);

    // Then
    assertThat(connected).isFalse();
  }
}
