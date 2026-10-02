package com.pompomhills.intelligence.meta;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * Short-lived, in-memory, single-use CSRF state tokens for the OAuth authorization flow. A state
 * value is valid once and expires after {@link #STATE_TTL}; it is removed as soon as it is consumed
 * or found expired, so it cannot be replayed.
 */
@Component
public class MetaOAuthStateStore {
  private static final Duration STATE_TTL = Duration.ofMinutes(10);
  private static final SecureRandom RANDOM = new SecureRandom();

  private final Map<String, Instant> pendingStates = new ConcurrentHashMap<>();
  private final Clock clock;

  public MetaOAuthStateStore(Clock clock) {
    this.clock = clock;
  }

  /** Issues a new random state value and records it as pending. */
  public String issue() {
    byte[] bytes = new byte[32];
    RANDOM.nextBytes(bytes);
    String state = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    pendingStates.put(state, clock.instant().plus(STATE_TTL));
    return state;
  }

  /**
   * Consumes a state value: returns true only if it was previously issued and has not expired. The
   * state is removed either way, so it can never be validated twice.
   */
  public boolean consume(String state) {
    if (state == null || state.isBlank()) {
      return false;
    }
    Instant expiresAt = pendingStates.remove(state);
    return expiresAt != null && clock.instant().isBefore(expiresAt);
  }
}
