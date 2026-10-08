package com.pompomhills.intelligence.workflow;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.quality.QualityMlClient;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClient;

class WorkflowTransportTest {
  @Test
  void artifactVerificationSendsHashDerivedImmutableModelVersion() throws Exception {
    var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    var received = new java.util.concurrent.atomic.AtomicReference<String>();
    server.createContext(
        "/v1/training/verify-artifact",
        exchange -> {
          received.set(
              new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
          byte[] response = "{\"verified\":true}".getBytes(StandardCharsets.UTF_8);
          exchange.getResponseHeaders().set("Content-Type", "application/json");
          exchange.sendResponseHeaders(200, response.length);
          exchange.getResponseBody().write(response);
          exchange.close();
        });
    server.start();
    try {
      var service =
          new com.pompomhills.intelligence.modelregistry.StatisticalTrainingService(
              null,
              RestClient.builder()
                  .baseUrl("http://127.0.0.1:" + server.getAddress().getPort())
                  .build(),
              new tools.jackson.databind.ObjectMapper());
      service.verify(
          "instagram",
          "models/statistical/fixture.json",
          Map.of("pipelineVersion", "grouped-ridge-72h-v1", "artifactSha256", "a".repeat(64)));
      assertThat(received.get()).contains("grouped-ridge-72h-v1-aaaaaaaaaaaa");
    } finally {
      server.stop(0);
    }
  }

  @Test
  void sendsCompleteJsonOverHttpOneAndPreservesBindingKeys() throws Exception {
    var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext(
        "/api/v1/workflow/review",
        exchange -> {
          String body =
              new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
          assertThat(body).contains("sourceVersion");
          assertThat(exchange.getProtocol()).isEqualTo("HTTP/1.1");
          byte[] result = "{\"bindingHash\":\"abc\"}".getBytes(StandardCharsets.UTF_8);
          exchange.sendResponseHeaders(200, result.length);
          exchange.getResponseBody().write(result);
          exchange.close();
        });
    server.start();
    try {
      var client =
          new QualityMlClient(
              "http://127.0.0.1:" + server.getAddress().getPort(), RestClient.builder());
      assertThat(client.workflow("review", Map.of("sourceVersion", "1")))
          .containsEntry("bindingHash", "abc");
    } finally {
      server.stop(0);
    }
  }

  @Test
  void creativeRoleAndReadinessReachOnlyTheirExplicitLocalPorts() throws Exception {
    var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext(
        "/api/v1/workflow/creative-role",
        exchange -> {
          assertThat(exchange.getRequestMethod()).isEqualTo("POST");
          var bytes =
              "{\"liveVerified\":false,\"providerCalls\":0}".getBytes(StandardCharsets.UTF_8);
          exchange.sendResponseHeaders(200, bytes.length);
          exchange.getResponseBody().write(bytes);
          exchange.close();
        });
    server.start();
    try {
      var client =
          new QualityMlClient(
              "http://127.0.0.1:" + server.getAddress().getPort(), RestClient.builder());
      assertThat(client.workflow("creative-role/readiness", Map.of()))
          .containsEntry("liveVerified", false);
      assertThat(client.workflow("creative-role", Map.of("role", "STORY", "prompt", "fixture")))
          .containsEntry("providerCalls", 0);
      org.assertj.core.api.Assertions.assertThatThrownBy(
              () -> client.workflow("../admin", Map.of()))
          .isInstanceOf(IllegalArgumentException.class);
    } finally {
      server.stop(0);
    }
  }
}
