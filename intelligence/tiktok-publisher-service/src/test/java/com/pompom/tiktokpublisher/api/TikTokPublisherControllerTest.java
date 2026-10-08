package com.pompom.tiktokpublisher.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import com.pompom.tiktokpublisher.service.TikTokPublishService;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class TikTokPublisherControllerTest {

  private static final String INTERNAL_TOKEN = "internal-secret";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void rejectsPublishWithoutInternalAuthentication() throws Exception {
    TikTokPublishService service = mock(TikTokPublishService.class);
    MockMvc mvc = mvc(service, configuredGuard(true));

    mvc.perform(
            post("/internal/v1/publish")
                .header(TikTokWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .header(TikTokWriteCapabilityGuard.CAPABILITY_HEADER, "tiktok_video")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isUnauthorized())
        .andExpect(
            content()
                .string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("secret"))));

    verifyNoInteractions(service);
  }

  @Test
  void rejectsPublishWhenWriteCapabilityIsDisabled() throws Exception {
    TikTokPublishService service = mock(TikTokPublishService.class);
    MockMvc mvc = mvc(service, configuredGuard(false));

    mvc.perform(
            post("/internal/v1/publish")
                .header(TikTokWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(TikTokWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .header(TikTokWriteCapabilityGuard.CAPABILITY_HEADER, "tiktok_video")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isForbidden());

    verifyNoInteractions(service);
  }

  @Test
  void returnsNormalizedPublishResultForAuthenticatedInternalCaller() throws Exception {
    TikTokPublishService service = mock(TikTokPublishService.class);
    PublishResult result =
        new PublishResult(
            PublishStatus.COMPLETED,
            "publish-1",
            null,
            "https://tiktok.example/video/1",
            "log-1",
            null,
            null,
            false);
    when(service.publish(any(PublishCommand.class), eq("tiktok_video"))).thenReturn(result);
    MockMvc mvc = mvc(service, configuredGuard(true));

    mvc.perform(
            post("/internal/v1/publish")
                .header(TikTokWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .header(TikTokWriteCapabilityGuard.CALLER_ENABLED_HEADER, "true")
                .header(TikTokWriteCapabilityGuard.CAPABILITY_HEADER, "tiktok_video")
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command())))
        .andExpect(status().isOk())
        .andExpect(content().json(OBJECT_MAPPER.writeValueAsString(result)));

    verify(service).publish(any(PublishCommand.class), eq("tiktok_video"));
  }

  @Test
  void reconciliationRequiresInternalAuthenticationButNotCallerWriteEnablement() throws Exception {
    TikTokPublishService service = mock(TikTokPublishService.class);
    TikTokPublishService.ReconcileCommand command =
        new TikTokPublishService.ReconcileCommand(
            UUID.randomUUID(), "tiktok_video", "account-1", "publish-1", null, "log-1");
    PublishResult result =
        new PublishResult(
            PublishStatus.RECONCILIATION_REQUIRED,
            "publish-1",
            null,
            null,
            "log-1",
            "reconciliation_required",
            "still processing",
            true);
    when(service.reconcile(any(TikTokPublishService.ReconcileCommand.class))).thenReturn(result);
    MockMvc mvc = mvc(service, configuredGuard(false));

    mvc.perform(
            post("/internal/v1/reconcile")
                .header(TikTokWriteCapabilityGuard.INTERNAL_TOKEN_HEADER, INTERNAL_TOKEN)
                .contentType("application/json")
                .content(OBJECT_MAPPER.writeValueAsString(command)))
        .andExpect(status().isOk())
        .andExpect(content().json(OBJECT_MAPPER.writeValueAsString(result)));

    verify(service).reconcile(any(TikTokPublishService.ReconcileCommand.class));
  }

  private MockMvc mvc(TikTokPublishService service, TikTokWriteCapabilityGuard guard) {
    return MockMvcBuilders.standaloneSetup(new TikTokPublisherController(service, guard)).build();
  }

  private TikTokWriteCapabilityGuard configuredGuard(boolean enabled) {
    return new TikTokWriteCapabilityGuard(
        enabled, enabled, false, INTERNAL_TOKEN, "access-token", "account-1");
  }

  private PublishCommand command() {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "idempotency-1",
        "account-1",
        "/asset/video.mp4",
        "a".repeat(64),
        "title",
        "caption",
        List.of("tag"),
        true,
        Map.of());
  }
}
