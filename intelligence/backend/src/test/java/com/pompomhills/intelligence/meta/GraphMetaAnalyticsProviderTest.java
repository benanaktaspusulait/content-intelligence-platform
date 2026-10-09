package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;

class GraphMetaAnalyticsProviderTest {
  @Test
  void delegatesPageAndMediaReadsThroughNeutralContract() {
    MetaPageContentService pages = mock(MetaPageContentService.class);
    MetaReelsService reels = mock(MetaReelsService.class);
    MetaPageContentResponse pageResponse = mock(MetaPageContentResponse.class);
    MetaReelAnalyticsResponse analyticsResponse = mock(MetaReelAnalyticsResponse.class);
    when(pages.getRecentContent()).thenReturn(pageResponse);
    when(reels.getAnalytics("media-1")).thenReturn(analyticsResponse);

    MetaAnalyticsProvider provider = new GraphMetaAnalyticsProvider(pages, reels);

    assertThat(provider.pageContent()).isSameAs(pageResponse);
    assertThat(provider.mediaAnalytics("media-1")).isSameAs(analyticsResponse);
    verify(pages).getRecentContent();
    verify(reels).getAnalytics("media-1");
  }
}
