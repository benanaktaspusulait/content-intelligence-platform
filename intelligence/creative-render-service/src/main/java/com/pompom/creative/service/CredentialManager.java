package com.pompom.creative.service;

import com.pompom.creative.domain.PlatformCredential;
import com.pompom.creative.oauth.OAuthService;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.oauth.dto.OAuthToken;
import com.pompom.creative.repository.PlatformCredentialRepository;
import com.pompom.creative.security.EncryptionService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Manages secure storage and retrieval of platform credentials. All tokens are encrypted at rest
 * using AES-256-GCM.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class CredentialManager {

  private final PlatformCredentialRepository credentialRepository;
  private final EncryptionService encryptionService;
  private final OAuthService oauthService;

  /**
   * Save or update platform credential with encryption.
   *
   * @param platform Target platform
   * @param token OAuth token to store
   * @return Saved credential entity
   */
  @Transactional
  public PlatformCredential saveCredential(PlatformType platform, OAuthToken token) {
    log.info("Saving credential for platform: {}", platform);

    // Find existing credential or create new
    PlatformCredential credential =
        credentialRepository
            .findByPlatform(platform)
            .orElse(
                PlatformCredential.builder().platform(platform).connectedAt(Instant.now()).build());

    // Encrypt tokens
    String encryptedAccessToken = encryptionService.encrypt(token.getAccessToken());
    String encryptedRefreshToken =
        token.getRefreshToken() != null ? encryptionService.encrypt(token.getRefreshToken()) : null;

    // Update credential
    credential.setAccessTokenEncrypted(encryptedAccessToken);
    credential.setRefreshTokenEncrypted(encryptedRefreshToken);
    credential.setTokenType(token.getTokenType());
    credential.setScope(token.getScope());
    credential.setExpiresAt(token.getExpiresAt());
    credential.setPlatformUserId(token.getPlatformUserId());
    credential.setPlatformUsername(token.getPlatformUsername());
    credential.setIsActive(true);
    credential.setLastRefreshedAt(Instant.now());

    PlatformCredential saved = credentialRepository.save(credential);
    log.info("Credential saved successfully: platform={}, id={}", platform, saved.getId());

    return saved;
  }

  /**
   * Get decrypted credential for a platform.
   *
   * @param platform Target platform
   * @return Decrypted OAuth token
   */
  @Transactional(readOnly = true)
  public Optional<OAuthToken> getCredential(PlatformType platform) {
    log.debug("Retrieving credential for platform: {}", platform);

    return credentialRepository
        .findByPlatformAndIsActiveTrue(platform)
        .map(
            credential -> {
              // Decrypt tokens
              String accessToken = encryptionService.decrypt(credential.getAccessTokenEncrypted());
              String refreshToken =
                  credential.getRefreshTokenEncrypted() != null
                      ? encryptionService.decrypt(credential.getRefreshTokenEncrypted())
                      : null;

              return OAuthToken.builder()
                  .accessToken(accessToken)
                  .refreshToken(refreshToken)
                  .tokenType(credential.getTokenType())
                  .scope(credential.getScope())
                  .expiresAt(credential.getExpiresAt())
                  .platformUserId(credential.getPlatformUserId())
                  .platformUsername(credential.getPlatformUsername())
                  .build();
            });
  }

  /**
   * Get active access token, refreshing if needed.
   *
   * @param platform Target platform
   * @return Valid access token
   */
  @Transactional
  public String getActiveAccessToken(PlatformType platform) {
    log.debug("Getting active access token for platform: {}", platform);

    PlatformCredential credential =
        credentialRepository
            .findByPlatformAndIsActiveTrue(platform)
            .orElseThrow(
                () -> new RuntimeException("No credential found for platform: " + platform));

    // Check if token needs refresh
    if (credential.willExpireSoon() && credential.getRefreshTokenEncrypted() != null) {
      log.info("Token will expire soon, refreshing: platform={}", platform);
      refreshIfNeeded(platform);

      // Reload credential after refresh
      credential =
          credentialRepository
              .findByPlatformAndIsActiveTrue(platform)
              .orElseThrow(() -> new RuntimeException("Failed to reload credential after refresh"));
    }

    // Decrypt and return access token
    return encryptionService.decrypt(credential.getAccessTokenEncrypted());
  }

  /**
   * Refresh credential if expired or expiring soon.
   *
   * @param platform Target platform
   * @return true if refreshed, false if not needed
   */
  @Transactional
  public boolean refreshIfNeeded(PlatformType platform) {
    log.info("Checking if refresh needed for platform: {}", platform);

    PlatformCredential credential =
        credentialRepository
            .findByPlatformAndIsActiveTrue(platform)
            .orElseThrow(
                () -> new RuntimeException("No credential found for platform: " + platform));

    // Check if refresh needed
    if (!credential.willExpireSoon()) {
      log.debug("Token still valid, no refresh needed: platform={}", platform);
      return false;
    }

    if (credential.getRefreshTokenEncrypted() == null) {
      log.warn("Token expiring but no refresh token available: platform={}", platform);
      return false;
    }

    try {
      // Decrypt refresh token
      String refreshToken = encryptionService.decrypt(credential.getRefreshTokenEncrypted());

      // Refresh via OAuth service
      OAuthToken newToken = oauthService.refreshAccessToken(platform, refreshToken);

      // Save new token
      saveCredential(platform, newToken);

      log.info("Token refreshed successfully: platform={}", platform);
      return true;

    } catch (Exception e) {
      log.error("Failed to refresh token: platform={}", platform, e);
      throw new RuntimeException("Token refresh failed: " + e.getMessage(), e);
    }
  }

  /**
   * Disconnect a platform by marking credential as inactive.
   *
   * @param platform Target platform
   */
  @Transactional
  public void disconnectPlatform(PlatformType platform) {
    log.info("Disconnecting platform: {}", platform);

    credentialRepository
        .findByPlatform(platform)
        .ifPresent(
            credential -> {
              credential.setIsActive(false);
              credentialRepository.save(credential);
              log.info("Platform disconnected: {}", platform);
            });
  }

  /**
   * Get all active platforms.
   *
   * @return List of active platform types
   */
  @Transactional(readOnly = true)
  public List<PlatformType> getActivePlatforms() {
    return credentialRepository.findByIsActiveTrue().stream()
        .map(PlatformCredential::getPlatform)
        .toList();
  }

  /**
   * Check if platform is connected.
   *
   * @param platform Target platform
   * @return true if connected and active
   */
  @Transactional(readOnly = true)
  public boolean isConnected(PlatformType platform) {
    return credentialRepository.existsByPlatformAndIsActiveTrue(platform);
  }
}
