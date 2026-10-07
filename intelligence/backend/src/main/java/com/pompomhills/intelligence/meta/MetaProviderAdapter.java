package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.Set;

/** Provider boundary for Meta authorization and explicitly supported token lifecycle operations. */
public interface MetaProviderAdapter {
  AuthorizationResult authorize(String code);

  default boolean isConfigured() {
    return true;
  }

  default String buildAuthorizationUrl(String state) {
    throw new UnsupportedOperationException("Meta authorization is not configured.");
  }

  default boolean supportsRefresh() {
    return false;
  }

  default TokenRefreshResult refresh(StoredTokens tokens) {
    throw new UnsupportedOperationException("Meta token refresh is not supported.");
  }

  default boolean supportsRevoke() {
    return false;
  }

  default void revoke(StoredTokens tokens) {
    throw new UnsupportedOperationException("Meta token revoke is not supported.");
  }

  record AuthorizationResult(
      String providerUserId,
      String facebookPageId,
      String instagramAccountId,
      String instagramAccountType,
      String userAccessToken,
      String pageAccessToken,
      String refreshToken,
      Set<String> grantedScopes,
      Instant issuedAt,
      Instant expiresAt,
      boolean facebookPageEligible,
      boolean instagramAccountEligible,
      String providerValidationReason) {
    public AuthorizationResult {
      grantedScopes = grantedScopes == null ? Set.of() : Set.copyOf(grantedScopes);
    }
  }

  record StoredTokens(String userAccessToken, String pageAccessToken, String refreshToken) {}

  record TokenRefreshResult(
      String userAccessToken,
      String pageAccessToken,
      String refreshToken,
      Instant issuedAt,
      Instant expiresAt) {}
}
