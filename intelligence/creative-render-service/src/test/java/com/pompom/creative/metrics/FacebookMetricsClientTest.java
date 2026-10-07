package com.pompom.creative.metrics;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.metrics.client.FacebookMetricsClient;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.CredentialManager;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class FacebookMetricsClientTest {

  @Mock private CredentialManager credentialManager;

  private MockRestServiceServer server;
  private FacebookMetricsClient client;

  @BeforeEach
  void setUp() {
    RestClient.Builder builder = RestClient.builder();
    server = MockRestServiceServer.bindTo(builder).build();
    client = new FacebookMetricsClient(credentialManager, builder, new ObjectMapper());
    when(credentialManager.getActiveAccessToken(PlatformType.FACEBOOK))
        .thenReturn("token-for-test");
  }

  @Test
  void readsFacebookVideoMetricsWithoutTurningMissingFieldsIntoZero() throws Exception {
    server
        .expect(requestTo(org.hamcrest.Matchers.containsString("/v18.0/video-1")))
        .andRespond(
            withSuccess(
                "{\"id\":\"video-1\",\"views\":1200,"
                    + "\"likes\":{\"data\":[],\"summary\":{\"total_count\":42}},"
                    + "\"comments\":{\"data\":[],\"summary\":{\"total_count\":7}},"
                    + "\"shares\":{\"count\":3}}",
                APPLICATION_JSON));

    VideoMetrics metrics = client.fetchMetrics("video-1");

    assertThat(metrics.getPlatform()).isEqualTo(PlatformType.FACEBOOK);
    assertThat(metrics.getViews()).isEqualTo(1200L);
    assertThat(metrics.getLikes()).isEqualTo(42L);
    assertThat(metrics.getComments()).isEqualTo(7L);
    assertThat(metrics.getShares()).isEqualTo(3L);
    assertThat(metrics.getImpressions()).isNull();
    server.verify();
  }
}
