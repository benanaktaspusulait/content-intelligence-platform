package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class MetaPublicCommentWebhookNormalizerTest {

  private final MetaPublicCommentWebhookNormalizer normalizer =
      new MetaPublicCommentWebhookNormalizer(new ObjectMapper());

  @Test
  void normalizesInstagramCommentEvents() {
    Optional<MetaPublicCommentWebhookNormalizer.NormalizedComment> result =
        normalizer.normalize(
            "{\"object\":\"instagram\",\"entry\":[{\"id\":\"ig-1\",\"time\":1700000000,\"changes\":[{\"field\":\"comments\",\"value\":{\"id\":\"comment-1\",\"text\":\"Love it\",\"from\":{\"id\":\"user-1\",\"username\":\"viewer\"},\"media\":{\"id\":\"media-1\"}}}]}]}");

    assertThat(result).isPresent();
    assertThat(result.orElseThrow())
        .satisfies(
            comment -> {
              assertThat(comment.platform()).isEqualTo(PlatformType.INSTAGRAM);
              assertThat(comment.accountId()).isEqualTo("ig-1");
              assertThat(comment.objectId()).isEqualTo("media-1");
              assertThat(comment.commentId()).isEqualTo("comment-1");
              assertThat(comment.text()).isEqualTo("Love it");
              assertThat(comment.authorId()).isEqualTo("user-1");
            });
  }

  @Test
  void normalizesFacebookPageFeedCommentEvents() {
    Optional<MetaPublicCommentWebhookNormalizer.NormalizedComment> result =
        normalizer.normalize(
            "{\"object\":\"page\",\"entry\":[{\"id\":\"page-1\",\"changes\":[{\"field\":\"feed\",\"value\":{\"item\":\"comment\",\"verb\":\"add\",\"comment_id\":\"comment-2\",\"post_id\":\"post-1\",\"message\":\"Nice\",\"from\":{\"id\":\"user-2\",\"name\":\"Viewer\"}}}]}]}");

    assertThat(result).isPresent();
    assertThat(result.orElseThrow().platform()).isEqualTo(PlatformType.FACEBOOK);
    assertThat(result.orElseThrow().accountId()).isEqualTo("page-1");
    assertThat(result.orElseThrow().objectId()).isEqualTo("post-1");
    assertThat(result.orElseThrow().commentId()).isEqualTo("comment-2");
    assertThat(result.orElseThrow().text()).isEqualTo("Nice");
  }

  @Test
  void ignoresNonCommentEvents() {
    assertThat(
            normalizer.normalize(
                "{\"object\":\"page\",\"entry\":[{\"id\":\"page-1\",\"changes\":[{\"field\":\"feed\",\"value\":{\"item\":\"status\"}}]}]}"))
        .isEmpty();
  }
}
