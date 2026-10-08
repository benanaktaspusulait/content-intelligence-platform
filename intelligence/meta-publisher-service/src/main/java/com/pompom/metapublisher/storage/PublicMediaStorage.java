package com.pompom.metapublisher.storage;

import com.pompom.publishercontract.PublishCommand;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

/** Provider-neutral boundary for producing an HTTPS URL that Meta can fetch. */
public interface PublicMediaStorage {

  Set<String> APPROVED_SIGNED_QUERY_KEYS =
      Set.of(
          "xamzalgorithm",
          "xamzdate",
          "xamzexpires",
          "xamzsignedheaders",
          "xamzsignature",
          "signature",
          "sig",
          "expires",
          "expiry",
          "st",
          "se",
          "sp",
          "sr",
          "sv");

  Optional<HostedMedia> host(PublishCommand command);

  void cleanup(String url);

  static boolean isSafeHttpsUrl(String value) {
    try {
      URI uri = URI.create(value);
      if (uri.getScheme() == null
          || !"https".equalsIgnoreCase(uri.getScheme())
          || uri.getHost() == null
          || uri.getUserInfo() != null
          || uri.getRawFragment() != null) {
        return false;
      }
      String query = uri.getRawQuery();
      if (query == null || query.isBlank()) {
        return true;
      }
      for (String parameter : query.split("&")) {
        String key = parameter.split("=", 2)[0];
        String decoded = URLDecoder.decode(key, StandardCharsets.UTF_8);
        String normalized = decoded.replaceAll("[^A-Za-z0-9]", "").toLowerCase(Locale.ROOT);
        if (!APPROVED_SIGNED_QUERY_KEYS.contains(normalized)) {
          return false;
        }
      }
      return true;
    } catch (RuntimeException ignored) {
      return false;
    }
  }

  record HostedMedia(String url, boolean owned) {}
}
