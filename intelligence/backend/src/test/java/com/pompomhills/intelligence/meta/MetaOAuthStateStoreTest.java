package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

class MetaOAuthStateStoreTest {
  @Test void stateIsSingleUse() {
    var store = new MetaOAuthStateStore(Clock.fixed(Instant.parse("2026-10-09T12:00:00Z"), ZoneOffset.UTC));
    String state = store.issue("owner");
    assertThat(store.consume(state, "owner")).isTrue();
    assertThat(store.consume(state, "owner")).isFalse();
  }

  @Test void stateCannotBeConsumedByAnotherOwner() {
    var store = new MetaOAuthStateStore(Clock.systemUTC());
    String state = store.issue("owner-a");
    assertThat(store.consume(state, "owner-b")).isFalse();
    assertThat(store.consume(state, "owner-a")).isFalse();
  }

  @Test void blankStateIsRejected() {
    var store = new MetaOAuthStateStore(Clock.systemUTC());
    assertThat(store.consume(null, "owner")).isFalse();
    assertThat(store.consume(" ", "owner")).isFalse();
  }
}
