package com.pompom.creative.config;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;

/** Simple rate limiting filter. Production should use Redis-based solution like Bucket4j. */
@Component
public class RateLimitingFilter implements Filter {

  private static final int MAX_REQUESTS_PER_MINUTE = 100;
  private final Map<String, AtomicInteger> requestCounts = new ConcurrentHashMap<>();

  @Override
  public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
      throws IOException, ServletException {

    HttpServletRequest httpRequest = (HttpServletRequest) request;
    HttpServletResponse httpResponse = (HttpServletResponse) response;

    String clientId = getClientId(httpRequest);
    AtomicInteger count = requestCounts.computeIfAbsent(clientId, k -> new AtomicInteger(0));

    if (count.incrementAndGet() > MAX_REQUESTS_PER_MINUTE) {
      httpResponse.setStatus(429);
      httpResponse.getWriter().write("{\"error\":\"Rate limit exceeded\"}");
      return;
    }

    chain.doFilter(request, response);
  }

  private String getClientId(HttpServletRequest request) {
    return request.getRemoteAddr();
  }
}
