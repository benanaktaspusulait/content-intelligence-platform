package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Secret-free, bounded provider account discovery result. */
public record MetaAccountDiscoveryResponse(
    UUID connectionId,
    String ownerIdentity,
    Status status,
    MetaConnectionStatus connectionStatus,
    List<PageTarget> pages,
    String selectedPageId,
    String selectedInstagramAccountId,
    Map<MetaCapability, MetaCapabilityStatus> capabilities,
    Instant expiresAt,
    String message,
    String failureReason) {

  public MetaAccountDiscoveryResponse {
    pages = pages == null ? List.of() : List.copyOf(pages);
    capabilities = capabilities == null ? Map.of() : Map.copyOf(capabilities);
  }

  public boolean connected() {
    return status == Status.AVAILABLE;
  }

  public List<PageTarget> targets() {
    return pages;
  }

  public List<PageTarget> pageTargets() {
    return pages;
  }

  public PageTarget selectedPage() {
    return pages.stream().filter(PageTarget::selected).findFirst().orElse(null);
  }

  public enum Status {
    AVAILABLE,
    DEGRADED,
    EXPIRED,
    REVOKED,
    NOT_CONFIGURED
  }

  public record PageTarget(
      String id,
      String name,
      String category,
      boolean accessTokenAvailable,
      boolean selected,
      MetaCapabilityStatus pageEligibility,
      Map<MetaCapability, MetaCapabilityStatus> capabilities,
      InstagramTarget instagramAccount) {

    public PageTarget {
      capabilities = capabilities == null ? Map.of() : Map.copyOf(capabilities);
    }

    public MetaCapabilityStatus eligibility() {
      return pageEligibility;
    }
  }

  public record InstagramTarget(
      String id,
      boolean selected,
      MetaCapabilityStatus mediaEligibility,
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {

    public InstagramTarget {
      capabilities = capabilities == null ? Map.of() : Map.copyOf(capabilities);
    }

    public boolean mediaEligible() {
      return mediaEligibility == MetaCapabilityStatus.SUPPORTED;
    }
  }
}
