package com.pompomhills.intelligence.meta;

import org.springframework.stereotype.Service;

/** Graph-backed implementation of the provider-neutral Meta analytics contract. */
@Service
public class GraphMetaAnalyticsProvider implements MetaAnalyticsProvider {
  private final MetaPageContentService pageContentService;
  private final MetaReelsService reelsService;

  public GraphMetaAnalyticsProvider(
      MetaPageContentService pageContentService, MetaReelsService reelsService) {
    this.pageContentService = pageContentService;
    this.reelsService = reelsService;
  }

  @Override
  public MetaPageContentResponse pageContent() {
    return pageContentService.getRecentContent();
  }

  @Override
  public MetaReelsResponse reels(String after, Integer limit) {
    return reelsService.listReels(after, limit);
  }

  @Override
  public MetaReelAnalyticsResponse mediaAnalytics(String mediaId) {
    return reelsService.getAnalytics(mediaId);
  }
}
