package com.pompom.creative.meta;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.CredentialManager;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * Facebook Page public-comment reply adapter. Disabled by default through MetaCommentReplyGuard.
 */
@Component
@RequiredArgsConstructor
public class FacebookCommentReplyAdapter implements MetaCommentReplyPort {

  private static final String GRAPH_API_BASE = "https://graph.facebook.com/v18.0";

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;
  private final MetaCommentReplyGuard guard;

  @Override
  public PlatformType platform() {
    return PlatformType.FACEBOOK;
  }

  @Override
  public SendResult sendApprovedReply(MetaCommentReply reply) {
    guard.assertAllowed(platform());
    String token = credentialManager.getActiveAccessToken(platform());
    String commentId = reply.getComment().getExternalCommentId();
    String uri =
        UriComponentsBuilder.fromUriString(GRAPH_API_BASE + "/" + commentId + "/comments")
            .queryParam("message", reply.getDraftText())
            .queryParam("access_token", token)
            .build()
            .encode()
            .toUriString();
    String body = restClientBuilder.build().post().uri(uri).retrieve().body(String.class);
    return parseResult(body, "Facebook comment reply failed");
  }

  private SendResult parseResult(String body, String failure) {
    try {
      JsonNode json = objectMapper.readTree(body);
      if (json.has("error"))
        return SendResult.failure(failure + ": " + json.path("error").path("message").asText());
      String id = json.path("id").asText(null);
      return id == null
          ? SendResult.failure(failure + ": provider id missing")
          : SendResult.success(id);
    } catch (Exception error) {
      throw new IllegalStateException(failure, error);
    }
  }
}
