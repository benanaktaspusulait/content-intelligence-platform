package com.pompom.creative.meta;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

/** Normalizes public Facebook Page and Instagram comment webhook payloads. */
@Component
@RequiredArgsConstructor
public class MetaPublicCommentWebhookNormalizer {

  private final ObjectMapper objectMapper;

  public Optional<NormalizedComment> normalize(String payload) {
    try {
      JsonNode root = objectMapper.readTree(payload);
      String object = root.path("object").asText();
      JsonNode entry =
          root.path("entry").isArray() && root.path("entry").size() > 0
              ? root.path("entry").get(0)
              : null;
      if (entry == null || !entry.path("changes").isArray()) return Optional.empty();
      for (JsonNode change : entry.path("changes")) {
        String field = change.path("field").asText();
        JsonNode value = change.path("value");
        if ("instagram".equalsIgnoreCase(object) && "comments".equals(field)) {
          JsonNode media = value.path("media");
          return build(
              PlatformType.INSTAGRAM,
              entry.path("id").asText(null),
              media.path("id").asText(null),
              value);
        }
        if ("page".equalsIgnoreCase(object)
            && "feed".equals(field)
            && "comment".equalsIgnoreCase(value.path("item").asText())) {
          return build(
              PlatformType.FACEBOOK,
              entry.path("id").asText(null),
              value.path("post_id").asText(null),
              value);
        }
      }
      return Optional.empty();
    } catch (Exception ignored) {
      return Optional.empty();
    }
  }

  private Optional<NormalizedComment> build(
      PlatformType platform, String accountId, String objectId, JsonNode value) {
    String commentId = text(value, "id", "comment_id");
    String text = text(value, "text", "message");
    if (accountId == null || objectId == null || commentId == null || text == null) {
      return Optional.empty();
    }
    JsonNode author = value.path("from");
    return Optional.of(
        new NormalizedComment(
            platform,
            accountId,
            objectId,
            commentId,
            text,
            text(value, "parent_id", "parent_comment_id"),
            author.path("id").asText(null),
            text(author, "username", "name"),
            text(value, "permalink", "permalink_url"),
            instant(value, "created_time", "timestamp")));
  }

  private String text(JsonNode node, String... fields) {
    for (String field : fields) {
      JsonNode value = node.path(field);
      if (!value.isMissingNode() && !value.isNull() && !value.asText().isBlank()) {
        return value.asText();
      }
    }
    return null;
  }

  private Instant instant(JsonNode node, String... fields) {
    String value = text(node, fields);
    if (value == null) return null;
    try {
      return value.chars().allMatch(Character::isDigit)
          ? Instant.ofEpochSecond(Long.parseLong(value))
          : Instant.parse(value);
    } catch (Exception ignored) {
      return null;
    }
  }

  public record NormalizedComment(
      PlatformType platform,
      String accountId,
      String objectId,
      String commentId,
      String text,
      String parentCommentId,
      String authorId,
      String authorDisplayName,
      String permalink,
      Instant providerCreatedAt) {}
}
