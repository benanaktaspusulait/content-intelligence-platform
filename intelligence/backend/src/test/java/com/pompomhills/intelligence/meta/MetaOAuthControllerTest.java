package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class MetaOAuthControllerTest {
  private MetaConnectionLifecycleService lifecycle;
  private MetaOAuthStateStore states;
  private MockMvc mvc;

  @BeforeEach
  void setUp() {
    lifecycle = mock(MetaConnectionLifecycleService.class);
    states = new MetaOAuthStateStore(Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC));
    MetaReadProperties properties =
        new MetaReadProperties(
            true,
            "v26.0",
            "page-1",
            "instagram-1",
            "",
            "",
            Duration.ofSeconds(5),
            Duration.ofSeconds(15),
            false,
            false,
            "owner-1");
    MetaOAuthController oauthController =
        new MetaOAuthController(lifecycle, states, properties);
    MetaConnectionController connectionController =
        new MetaConnectionController(mock(MetaConnectionService.class), lifecycle);
    mvc = MockMvcBuilders.standaloneSetup(oauthController, connectionController).build();
    when(lifecycle.isConfigured()).thenReturn(true);
    when(lifecycle.buildAuthorizationUrl(anyString()))
        .thenAnswer(invocation -> "https://meta.test/oauth?state=" + invocation.getArgument(0));
  }

  @Test
  void callbackConsumesStateAndRedirectsWithoutReturningConnectionSecrets() throws Exception {
    MvcResult start = mvc.perform(get("/api/v1/meta/oauth/start")).andExpect(status().isFound()).andReturn();
    String location = start.getResponse().getHeader("Location");
    assertThat(location).isNotNull();
    String state =
        org.springframework.web.util.UriComponentsBuilder.fromUriString(location)
            .build()
            .getQueryParams()
            .getFirst("state");
    assertThat(state).isNotBlank();

    MetaConnectionResponse success =
        new MetaConnectionResponse(
            MetaConnectionResponse.Status.CONNECTED,
            true,
            true,
            null,
            null,
            Instant.parse("2026-10-01T12:00:00Z"),
            "v26.0",
            java.util.List.of(),
            java.util.List.of(),
            MetaConnectionResponse.PageManagementVerification.VERIFIED,
            "connected",
            java.util.UUID.randomUUID(),
            "owner-1",
            MetaConnectionStatus.CONNECTED,
            java.util.List.of("pages_read_engagement"),
            Map.of(),
            Instant.parse("2026-10-01T13:00:00Z"),
            null);
    when(lifecycle.completeAuthorization("code", state)).thenReturn(success);

    mvc.perform(
            get("/api/v1/meta/oauth/callback")
                .param("code", "code")
                .param("state", state))
        .andExpect(status().isFound())
        .andExpect(header().string("Location", "/meta/connection?meta_oauth=connected"));

    mvc.perform(
            get("/api/v1/meta/oauth/callback")
                .param("code", "code")
                .param("state", state))
        .andExpect(status().isFound())
        .andExpect(header().string("Location", "/meta/connection?meta_oauth=invalid_state"));
  }

  @Test
  void lifecycleEndpointsReturnStatusOnly() throws Exception {
    java.util.UUID id = java.util.UUID.randomUUID();
    MetaConnectionResponse response =
        new MetaConnectionResponse(
            MetaConnectionResponse.Status.DEGRADED,
            true,
            true,
            null,
            null,
            null,
            "v26.0",
            java.util.List.of(),
            java.util.List.of(),
            MetaConnectionResponse.PageManagementVerification.UNAVAILABLE,
            "expired",
            id,
            "owner-1",
            MetaConnectionStatus.EXPIRED,
            java.util.List.of("pages_read_engagement"),
            Map.of(MetaCapability.META_FACEBOOK_ANALYTICS_READ, MetaCapabilityStatus.TOKEN_EXPIRED),
            Instant.parse("2026-10-01T11:00:00Z"),
            "refresh unsupported");
    when(lifecycle.refreshIfNeeded(id)).thenReturn(response);
    when(lifecycle.disconnect(id)).thenReturn(response);

    mvc.perform(post("/api/v1/meta/connection/refresh").param("connectionId", id.toString()))
        .andExpect(status().isOk())
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath(
                    "$.connectionStatus")
                .value("EXPIRED"))
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath(
                    "$.userAccessToken")
                .doesNotExist())
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath(
                    "$.refreshToken")
                .doesNotExist());

    mvc.perform(post("/api/v1/meta/connection/disconnect").param("connectionId", id.toString()))
        .andExpect(status().isOk())
        .andExpect(
            org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath(
                    "$.connectionStatus")
                .value("EXPIRED"));
  }
}
