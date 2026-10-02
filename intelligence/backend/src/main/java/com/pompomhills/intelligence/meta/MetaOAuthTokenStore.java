package com.pompomhills.intelligence.meta;

import java.util.concurrent.atomic.AtomicReference;
import org.springframework.stereotype.Component;

/**
 * Holds the tokens obtained via the OAuth authorization flow, in process memory only. Neither token
 * is ever persisted, logged, or returned to the browser.
 *
 * <p>Two tokens are kept because they serve different Graph API contexts: the Page token is used
 * for content/media reads against the configured Page and Instagram account, while the user token
 * is required for user-context calls such as {@code GET /me/accounts} (pages_show_list
 * verification). Both are derived from the same successful authorization and take precedence over
 * their statically configured fallbacks when present.
 */
@Component
public class MetaOAuthTokenStore {
  private final AtomicReference<String> userAccessToken = new AtomicReference<>();
  private final AtomicReference<String> pageAccessToken = new AtomicReference<>();

  public void setUserAccessToken(String token) {
    userAccessToken.set(token == null || token.isBlank() ? null : token);
  }

  public String getUserAccessToken() {
    return userAccessToken.get();
  }

  public void setPageAccessToken(String token) {
    pageAccessToken.set(token == null || token.isBlank() ? null : token);
  }

  public String getPageAccessToken() {
    return pageAccessToken.get();
  }

  public boolean hasToken() {
    return pageAccessToken.get() != null;
  }
}
