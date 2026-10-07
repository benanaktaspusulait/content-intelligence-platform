package com.pompom.creative.webhook;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.WebhookEventRepository;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;

class WebhookServiceSignatureTest {

  private final WebhookService service =
      new WebhookService(
          mock(WebhookEventRepository.class),
          mock(PublicationJobRepository.class),
          new ObjectMapper());

  @Test
  void acceptsMetaSha256HexSignature() throws Exception {
    String payload = "{}";

    assertThat(
            service.verifySignature(
                PlatformType.FACEBOOK, payload, "sha256=" + hmacHex(payload, "secret"), "secret"))
        .isTrue();
  }

  @Test
  void preservesBase64SignatureContractForNonMetaWebhooks() throws Exception {
    String payload = "{}";

    assertThat(
            service.verifySignature(
                PlatformType.TIKTOK, payload, hmacBase64(payload, "secret"), "secret"))
        .isTrue();
  }

  private String hmacHex(String payload, String secret) throws Exception {
    return HexFormat.of().formatHex(hmac(payload, secret));
  }

  private String hmacBase64(String payload, String secret) throws Exception {
    return Base64.getEncoder().encodeToString(hmac(payload, secret));
  }

  private byte[] hmac(String payload, String secret) throws Exception {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
    return mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
  }
}
