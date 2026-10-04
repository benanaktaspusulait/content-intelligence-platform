package com.pompom.creative.oauth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.UUID;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OAuthStateService {

  private static final Duration STATE_TTL = Duration.ofMinutes(10);
  private final OAuthStateRepository repository;

  public OAuthStateService(OAuthStateRepository repository) {
    this.repository = repository;
  }

  @Transactional
  public String issue(PlatformType platform) {
    String rawState = UUID.randomUUID().toString() + UUID.randomUUID();
    repository.save(
        OAuthState.builder()
            .stateHash(hash(rawState))
            .platform(platform)
            .expiresAt(Instant.now().plus(STATE_TTL))
            .build());
    return rawState;
  }

  @Transactional
  public PlatformType consume(String rawState) {
    if (rawState == null || rawState.isBlank()) {
      throw new IllegalArgumentException("OAuth state is required");
    }
    String stateHash = hash(rawState);
    OAuthState state =
        repository
            .findById(stateHash)
            .orElseThrow(() -> new IllegalArgumentException("Invalid OAuth state"));
    Instant now = Instant.now();
    if (repository.consume(stateHash, now) != 1) {
      throw new IllegalArgumentException("OAuth state is expired or already consumed");
    }
    return state.getPlatform();
  }

  @Scheduled(cron = "0 0 * * * *")
  @Transactional
  public void purgeExpired() {
    repository.deleteByExpiresAtBefore(Instant.now().minus(Duration.ofDays(1)));
  }

  private String hash(String value) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception error) {
      throw new IllegalStateException("Unable to hash OAuth state", error);
    }
  }
}
