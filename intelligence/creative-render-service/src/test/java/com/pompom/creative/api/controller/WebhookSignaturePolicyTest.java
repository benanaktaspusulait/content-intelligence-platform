package com.pompom.creative.api.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompom.creative.meta.MetaPublicCommentIngestionService;
import com.pompom.creative.meta.MetaPublicCommentWebhookNormalizer;
import com.pompom.creative.webhook.WebhookService;
import java.nio.charset.StandardCharsets;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class WebhookSignaturePolicyTest {

  private final WebhookService webhookService = mock(WebhookService.class);
  private final MetaPublicCommentWebhookNormalizer normalizer =
      mock(MetaPublicCommentWebhookNormalizer.class);
  private final MetaPublicCommentIngestionService ingestion =
      mock(MetaPublicCommentIngestionService.class);
  private MockMvc mvc;
  private WebhookController controller;

  @BeforeEach
  void setUp() {
    controller = new WebhookController(webhookService, normalizer, ingestion);
    ReflectionTestUtils.setField(controller, "facebookWebhookSecret", "secret");
    ReflectionTestUtils.setField(controller, "instagramWebhookSecret", "secret");
    ReflectionTestUtils.setField(controller, "metaSignatureRequired", true);
    mvc = MockMvcBuilders.standaloneSetup(controller).build();
  }

  @Test
  void rejectsFacebookWebhookWithoutSignature() throws Exception {
    mvc.perform(post("/api/v1/webhooks/facebook").content("{}"))
        .andExpect(status().isUnauthorized());
  }

  @Test
  void rejectsInstagramWebhookWithInvalidSignature() throws Exception {
    mvc.perform(
            post("/api/v1/webhooks/instagram")
                .header("X-Hub-Signature-256", "sha256=invalid")
                .content("{}"))
        .andExpect(status().isUnauthorized());
  }

  @Test
  void acceptsFacebookWebhookWithValidSignature() throws Exception {
    String payload = "{}";
    org.mockito.Mockito.when(
            webhookService.verifySignature(
                any(), org.mockito.ArgumentMatchers.eq(payload), any(), any()))
        .thenReturn(true);
    mvc.perform(
            post("/api/v1/webhooks/facebook")
                .header("X-Hub-Signature-256", "sha256=" + hmac(payload, "secret"))
                .content(payload))
        .andExpect(status().isOk());

    verify(webhookService).receiveWebhook(any(), any(), any());
  }

  private String hmac(String payload, String secret) throws Exception {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
    return java.util.Base64.getEncoder()
        .encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
  }
}
