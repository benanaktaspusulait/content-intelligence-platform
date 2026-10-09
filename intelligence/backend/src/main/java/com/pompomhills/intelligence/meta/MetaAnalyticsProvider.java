package com.pompomhills.intelligence.meta;

/**
 * Provider-neutral read-only analytics boundary.
 *
 * <p>Callers depend on this contract rather than selecting a Graph client or publication adapter
 * directly. Provider-specific authentication, pagination and availability mapping stay behind the
 * implementation.
 */
public interface MetaAnalyticsProvider {
  MetaPageContentResponse pageContent();

  MetaReelsResponse reels(String after, Integer limit);

  MetaReelAnalyticsResponse mediaAnalytics(String mediaId);
}
