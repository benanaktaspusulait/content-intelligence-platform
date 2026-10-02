package com.pompom.creative.oauth.dto;

import java.time.Instant;
import lombok.Builder;
import lombok.Data;

/** OAuth token response DTO. */
@Data
@Builder
public class OAuthToken {
  private String accessToken;
  private String refreshToken;
  private String tokenType;
  private Long expiresIn; // Seconds until expiration
  private Instant expiresAt;
  private String scope;
  private String platformUserId;
  private String platformUsername;

  public boolean isExpired() {
    if (expiresAt == null) {
      return false;
    }
    return Instant.now().isAfter(expiresAt);
  }

  public boolean willExpireSoon() {
    if (expiresAt == null) {
      return false;
    }
    // Consider expired if less than 5 minutes remaining
    return Instant.now().plusSeconds(300).isAfter(expiresAt);
  }
}
