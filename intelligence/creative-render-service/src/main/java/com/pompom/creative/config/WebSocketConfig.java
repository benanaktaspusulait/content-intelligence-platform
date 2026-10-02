package com.pompom.creative.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * WebSocket configuration for real-time updates.
 *
 * <p>Architecture: - STOMP protocol over WebSocket - Simple in-memory message broker for /topic
 * (broadcast) and /queue (user-specific) - Client endpoint: /ws - Application destination prefix:
 * /app
 *
 * <p>Topics: - /topic/render/progress - Render job progress updates (broadcast) -
 * /topic/metrics/updates - Metrics collection updates (broadcast) - /topic/performance/alerts -
 * Performance alerts (broadcast) - /queue/notifications - User-specific notifications
 *
 * <p>Usage: Frontend connects to ws://localhost:8080/ws Subscribes to topics:
 * client.subscribe('/topic/render/progress', callback) Sends messages:
 * client.send('/app/render/start', {}, JSON.stringify(data))
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

  @Override
  public void configureMessageBroker(MessageBrokerRegistry registry) {
    // Enable simple in-memory message broker
    // /topic = broadcast to all subscribers
    // /queue = user-specific messages
    registry.enableSimpleBroker("/topic", "/queue");

    // Application destination prefix
    // Messages sent to /app/* are routed to @MessageMapping methods
    registry.setApplicationDestinationPrefixes("/app");

    // User destination prefix (for user-specific messages)
    registry.setUserDestinationPrefix("/user");
  }

  @Override
  public void registerStompEndpoints(StompEndpointRegistry registry) {
    // Register WebSocket endpoint
    // Clients connect to ws://localhost:8080/ws
    registry
        .addEndpoint("/ws")
        .setAllowedOriginPatterns("*") // Allow all origins (configure for production)
        .withSockJS(); // Enable SockJS fallback for browsers without WebSocket support
  }
}
