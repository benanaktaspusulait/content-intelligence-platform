package com.pompom.creative.domain;

import com.pompom.creative.oauth.PlatformType;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Stores OAuth credentials for connected social media platforms. Access/refresh tokens are
 * encrypted before storage.
 */
@Entity
@Table(name = "platform_credentials")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PlatformCredential {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, unique = true, length = 20)
  private PlatformType platform;

  @Column(name = "platform_user_id", length = 100)
  private String platformUserId;

  @Column(name = "platform_username", length = 100)
  private String platformUsername;

  @Column(name = "access_token_encrypted", columnDefinition = "TEXT", nullable = false)
  private String accessTokenEncrypted;

  @Column(name = "refresh_token_encrypted", columnDefinition = "TEXT")
  private String refreshTokenEncrypted;

  @Column(name = "token_type", length = 50)
  private String tokenType;

  @Column(name = "scope", columnDefinition = "TEXT")
  private String scope;

  @Column(name = "expires_at")
  private Instant expiresAt;

  @Column(name = "is_active", nullable = false)
  private Boolean isActive = true;

  @Column(name = "last_refreshed_at")
  private Instant lastRefreshedAt;

  @Column(name = "connected_at", nullable = false)
  private Instant connectedAt = Instant.now();

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt = Instant.now();

  @PreUpdate
  public void preUpdate() {
    this.updatedAt = Instant.now();
  }

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
