package com.pompomhills.intelligence.meta;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/** Short-lived, in-memory, owner-bound, single-use CSRF state for the Meta OAuth flow. */
@Component
public class MetaOAuthStateStore {
  private static final Duration STATE_TTL = Duration.ofMinutes(10);
  private static final SecureRandom RANDOM = new SecureRandom();

  private final Map<String, PendingState> pendingStates = new ConcurrentHashMap<>();
  private final Clock clock;

  public MetaOAuthStateStore(Clock clock) {
    this.clock = clock;
  }

  /** Compatibility overload for the default single-owner deployment. */
  public String issue() {
    return issue("default");
  }

  /** Issues a state value bound to the explicit application owner key. */
  public String issue(String ownerKey) {
    byte[] bytes = new byte[32];
    RANDOM.nextBytes(bytes);
    String state = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    pendingStates.put(
        state,
        new PendingState(
            normalizeOwnerKey(ownerKey), clock.instant().plus(STATE_TTL)));
    return state;
  }

  /** Compatibility overload for the default single-owner deployment. */
  public boolean consume(String state) {
    return consume(state, "default");
  }

  /** Consumes a state only when it belongs to the requested owner and is not expired. */
  public boolean consume(String state, String ownerKey) {
    if (state == null || state.isBlank()) {
      return false;
    }
    PendingState pending = pendingStates.remove(state);
    return pending != null
        && normalizeOwnerKey(ownerKey).equals(pending.ownerKey())
        && clock.instant().isBefore(pending.expiresAt());
  }

  private String normalizeOwnerKey(String ownerKey) {
    String normalized = ownerKey == null ? "" : ownerKey.trim();
    return normalized.isBlank() ? "default" : normalized;
  }

  private record PendingState(String ownerKey, Instant expiresAt) {}
}
