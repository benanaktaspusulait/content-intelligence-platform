package com.pompom.publishercontract;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Provider-neutral command sent from the publication control plane to an internal publisher.
 *
 * <p>The command is used by {@code POST /internal/v1/publish}; credentials and provider tokens are
 * owned by the target publisher service and are intentionally not part of this payload. The
 * provider-options map accepts only documented non-secret publication metadata keys: privacy,
 * privacy_level, privacy_status, category_id, default_language, made_for_kids, duet/comment/stitch
 * controls, video_cover_timestamp_ms, tags, targeting, published, scheduled_publish_time,
 * caption_entities, location_id, and share_to_feed.
 */
public record PublishCommand(
    @NotNull UUID publicationJobId,
    @NotNull UUID publicationAttemptId,
    @NotBlank String idempotencyKey,
    @NotBlank String platformAccountId,
    @NotBlank String assetReference,
    @NotBlank @Pattern(regexp = "^[0-9a-fA-F]{64}$") String assetSha256,
    String title,
    String caption,
    List<String> hashtags,
    boolean isPrivate,
    Map<String, String> providerOptions) {

  private static final Set<String> ALLOWED_OPTION_KEYS =
      Set.of(
          "privacy",
          "privacy_level",
          "privacy_status",
          "category_id",
          "default_language",
          "made_for_kids",
          "disable_duet",
          "disable_comment",
          "disable_stitch",
          "duet_enabled",
          "comment_enabled",
          "stitch_enabled",
          "video_cover_timestamp_ms",
          "tags",
          "targeting",
          "published",
          "scheduled_publish_time",
          "caption_entities",
          "location_id",
          "share_to_feed");
  private static final Set<String> CREDENTIAL_OPTION_KEY_MARKERS =
      Set.of(
          "api",
          "key",
          "auth",
          "authorization",
          "bearer",
          "client",
          "credential",
          "oauth",
          "password",
          "secret",
          "token");

  public PublishCommand {
    hashtags = hashtags == null ? List.of() : List.copyOf(hashtags);
    providerOptions = normalizeProviderOptions(providerOptions);
  }

  private static Map<String, String> normalizeProviderOptions(Map<String, String> options) {
    if (options == null) {
      return Map.of();
    }

    for (String key : options.keySet()) {
      if (key == null || isCredentialOptionKey(key)) {
        throw new IllegalArgumentException(
            "providerOptions cannot contain credential-like option key: " + key);
      }
      if (!ALLOWED_OPTION_KEYS.contains(key)) {
        throw new IllegalArgumentException("Unknown providerOptions key: " + key);
      }
    }
    return Map.copyOf(options);
  }

  private static boolean isCredentialOptionKey(String key) {
    String normalizedKey = key.replaceAll("[^A-Za-z0-9]", "").toLowerCase(Locale.ROOT);
    return CREDENTIAL_OPTION_KEY_MARKERS.stream().anyMatch(normalizedKey::contains);
  }
}
