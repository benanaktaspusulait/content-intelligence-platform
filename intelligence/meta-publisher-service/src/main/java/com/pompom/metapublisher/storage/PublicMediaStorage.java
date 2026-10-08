package com.pompom.metapublisher.storage;

import com.pompom.publishercontract.PublishCommand;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Optional;

/** Provider-neutral boundary for producing an HTTPS URL that Meta can fetch. */
public interface PublicMediaStorage {

  Optional<HostedMedia> host(PublishCommand command);

  void cleanup(String url);

  static boolean isSafeHttpsUrl(String value) {
    try {
      URI uri = URI.create(value);
      if (!"https".equalsIgnoreCase(uri.getScheme())
          || uri.getHost() == null
          || (uri.getUserInfo() != null && !uri.getUserInfo().isBlank())) {
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
        if (normalized.contains("accesstoken")
            || normalized.equals("token")
            || normalized.contains("authorization")
            || normalized.contains("password")
            || normalized.contains("secret")
            || normalized.contains("apikey")
            || normalized.contains("credential")
            || normalized.contains("clientsecret")
            || normalized.contains("oauth")) {
          return false;
        }
      }
      return true;
    } catch (IllegalArgumentException ignored) {
      return false;
    }
  }

  record HostedMedia(String url, boolean owned) {}
}
