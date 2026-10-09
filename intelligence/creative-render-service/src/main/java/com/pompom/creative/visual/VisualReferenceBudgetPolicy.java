package com.pompom.creative.visual;

import java.math.BigDecimal;

/** Separate, explicit budgets for planning calls. Planning itself never consumes a budget. */
public record VisualReferenceBudgetPolicy(
    BigDecimal promptCredits, BigDecimal imageCredits, BigDecimal visionCredits, BigDecimal videoCredits, int maxRetries) {
  public VisualReferenceBudgetPolicy {
    if (maxRetries < 0) throw new IllegalArgumentException("maxRetries must be non-negative");
    if (promptCredits == null || imageCredits == null || visionCredits == null || videoCredits == null) throw new IllegalArgumentException("All visual reference budgets are required");
    if (promptCredits.signum() < 0 || imageCredits.signum() < 0 || visionCredits.signum() < 0 || videoCredits.signum() < 0) throw new IllegalArgumentException("Budgets cannot be negative");
  }

  public boolean allowsRetry(int attempt) { return attempt >= 0 && attempt < maxRetries; }
}
