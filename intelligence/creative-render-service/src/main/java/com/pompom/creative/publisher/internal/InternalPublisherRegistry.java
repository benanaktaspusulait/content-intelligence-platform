package com.pompom.creative.publisher.internal;

import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import java.util.EnumMap;
import java.util.Map;

public final class InternalPublisherRegistry {
  private final Map<PlatformType, PlatformPublisher> clients;

  public InternalPublisherRegistry(Map<PlatformType, PlatformPublisher> clients) {
    this.clients = new EnumMap<>(clients);
  }

  public PlatformPublisher get(PlatformType platform) {
    return clients.get(platform);
  }
}
