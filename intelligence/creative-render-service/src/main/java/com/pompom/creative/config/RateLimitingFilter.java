package com.pompom.creative.config;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/** Simple rate limiting filter. Production should use Redis-based solution like Bucket4j. */
@Component
public class RateLimitingFilter implements Filter {

  private static final int MAX_REQUESTS_PER_MINUTE = 100;
  private static final Duration WINDOW = Duration.ofMinutes(1);
  private final Map<String, WindowCounter> requestCounts = new ConcurrentHashMap<>();
  private final Clock clock = Clock.systemUTC();

  @Override
  public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
      throws IOException, ServletException {

    HttpServletRequest httpRequest = (HttpServletRequest) request;
    HttpServletResponse httpResponse = (HttpServletResponse) response;

    String clientId = getClientId(httpRequest);
    Instant now = clock.instant();
    WindowCounter count =
        requestCounts.compute(
            clientId,
            (ignored, current) ->
                current == null || !now.isBefore(current.windowStart.plus(WINDOW))
                    ? new WindowCounter(now, 1)
                    : new WindowCounter(current.windowStart, current.count + 1));

    if (count.count > MAX_REQUESTS_PER_MINUTE) {
      httpResponse.setStatus(429);
      httpResponse.getWriter().write("{\"error\":\"Rate limit exceeded\"}");
      return;
    }

    chain.doFilter(request, response);
  }

  private String getClientId(HttpServletRequest request) {
    return request.getRemoteAddr();
  }

  private record WindowCounter(Instant windowStart, int count) {}
}
