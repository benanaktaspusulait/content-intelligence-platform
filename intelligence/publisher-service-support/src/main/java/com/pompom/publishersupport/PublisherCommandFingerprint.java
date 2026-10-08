package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishCommand;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;

/**
 * Computes a stable, non-secret identity for a publish command independent of its idempotency key.
 */
public final class PublisherCommandFingerprint {

  private PublisherCommandFingerprint() {}

  public static String sha256(PublishCommand command) {
    Objects.requireNonNull(command, "command");
    String canonical =
        String.join(
            "\n",
            field(command.publicationJobId().toString()),
            field(command.publicationAttemptId().toString()),
            field(command.platformAccountId()),
            field(command.assetReference()),
            field(command.assetSha256()),
            field(command.title()),
            field(command.caption()),
            field(list(command.hashtags())),
            field(Boolean.toString(command.isPrivate())),
            field(map(command.providerOptions())));
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256")
                  .digest(canonical.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }

  private static String list(Iterable<String> values) {
    StringBuilder canonical = new StringBuilder(field(Integer.toString(size(values))));
    for (String value : values) {
      canonical.append(field(value));
    }
    return canonical.toString();
  }

  private static int size(Iterable<String> values) {
    int count = 0;
    for (String ignored : values) {
      count++;
    }
    return count;
  }

  private static String map(Map<String, String> values) {
    StringBuilder canonical = new StringBuilder(field(Integer.toString(values.size())));
    values.entrySet().stream()
        .sorted(Map.Entry.comparingByKey())
        .forEach(entry -> canonical.append(field(entry.getKey())).append(field(entry.getValue())));
    return canonical.toString();
  }

  private static String field(String value) {
    return value == null ? "-1:" : value.length() + ":" + value;
  }
}
