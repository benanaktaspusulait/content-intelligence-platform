package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.MetaComment;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.CredentialManager;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaCommentReplyAdapterTest {

  @Test
  void facebookAdapterUsesBearerHeaderAndDoesNotPutTokenInUri() {
    CredentialManager credentials = org.mockito.Mockito.mock(CredentialManager.class);
    when(credentials.getActiveAccessToken(PlatformType.FACEBOOK)).thenReturn("token");
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    server
        .expect(
            requestTo(
                org.hamcrest.Matchers.allOf(
                    org.hamcrest.Matchers.containsString("/comment-1/comments"),
                    org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("access_token")))))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer token"))
        .andRespond(withSuccess("{\"id\":\"fb-reply-1\"}", MediaType.APPLICATION_JSON));

    MetaCommentReplyPort adapter =
        new FacebookCommentReplyAdapter(
            credentials, builder, new ObjectMapper(), new MetaCommentReplyGuard(true));

    MetaCommentReplyPort.SendResult result =
        adapter.sendApprovedReply(reply(PlatformType.FACEBOOK));

    assertThat(result.success()).isTrue();
    assertThat(result.providerReplyId()).isEqualTo("fb-reply-1");
    server.verify();
  }

  @Test
  void instagramAdapterUsesBearerHeaderAndDoesNotPutTokenInUri() {
    CredentialManager credentials = org.mockito.Mockito.mock(CredentialManager.class);
    when(credentials.getActiveAccessToken(PlatformType.INSTAGRAM)).thenReturn("token");
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    server
        .expect(
            requestTo(
                org.hamcrest.Matchers.allOf(
                    org.hamcrest.Matchers.containsString("/comment-1/replies"),
                    org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("access_token")))))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer token"))
        .andRespond(withSuccess("{\"id\":\"ig-reply-1\"}", MediaType.APPLICATION_JSON));

    MetaCommentReplyPort adapter =
        new InstagramCommentReplyAdapter(
            credentials, builder, new ObjectMapper(), new MetaCommentReplyGuard(true));

    MetaCommentReplyPort.SendResult result =
        adapter.sendApprovedReply(reply(PlatformType.INSTAGRAM));

    assertThat(result.success()).isTrue();
    assertThat(result.providerReplyId()).isEqualTo("ig-reply-1");
    server.verify();
  }

  private MetaCommentReply reply(PlatformType platform) {
    return MetaCommentReply.builder()
        .idempotencyKey("reply-1")
        .draftText("Thanks!")
        .status(MetaCommentReply.Status.APPROVED)
        .comment(
            MetaComment.builder()
                .externalCommentId("comment-1")
                .thread(MetaCommentThread.builder().platform(platform).build())
                .text("Nice")
                .build())
        .build();
  }
}
