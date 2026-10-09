package com.pompom.creative.visual;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class VisualReferenceBudgetPolicyTest {
  @Test void keepsBudgetsSeparatedAndBoundsRetries() {
    var policy = new VisualReferenceBudgetPolicy(new BigDecimal("1"), new BigDecimal("2"), new BigDecimal("3"), new BigDecimal("4"), 2);
    assertThat(policy.promptCredits()).isEqualByComparingTo("1");
    assertThat(policy.allowsRetry(0)).isTrue();
    assertThat(policy.allowsRetry(2)).isFalse();
  }

  @Test void rejectsNegativeBudgets() {
    assertThatThrownBy(() -> new VisualReferenceBudgetPolicy(BigDecimal.ONE, BigDecimal.ONE, BigDecimal.ONE, BigDecimal.ONE.negate(), 1)).isInstanceOf(IllegalArgumentException.class);
  }
}
