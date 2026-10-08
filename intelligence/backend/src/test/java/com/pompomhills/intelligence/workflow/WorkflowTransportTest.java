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
}
