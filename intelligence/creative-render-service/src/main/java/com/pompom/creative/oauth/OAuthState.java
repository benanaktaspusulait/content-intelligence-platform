package com.pompom.creative.oauth;

import jakarta.persistence.*;
import java.time.Instant;
import lombok.*;

@Entity
@Table(name = "oauth_states")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OAuthState {

  @Id
  @Column(name = "state_hash", length = 64)
  private String stateHash;

  @Enumerated(EnumType.STRING)
  @Column(name = "platform", nullable = false, length = 20)
  private PlatformType platform;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "consumed_at")
  private Instant consumedAt;

  @Builder.Default
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt = Instant.now();
}
