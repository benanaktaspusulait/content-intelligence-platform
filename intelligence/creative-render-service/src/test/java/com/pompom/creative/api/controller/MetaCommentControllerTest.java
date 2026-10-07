package com.pompom.creative.api.controller;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompom.creative.meta.MetaCommentModerationService;
import com.pompom.creative.meta.MetaCommentReplyDeliveryService;
import com.pompom.creative.oauth.MetaCommentReplyDisabledException;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class MetaCommentControllerTest {

  private final MetaCommentModerationService moderation = mock(MetaCommentModerationService.class);
  private final MetaCommentReplyDeliveryService delivery =
      mock(MetaCommentReplyDeliveryService.class);
  private MockMvc mvc;
  private UUID replyId;

  @BeforeEach
  void setUp() {
    replyId = UUID.randomUUID();
    mvc = MockMvcBuilders.standaloneSetup(new MetaCommentController(moderation, delivery)).build();
  }

  @Test
  void sendsApprovedReplyThroughDeliveryService() throws Exception {
    when(delivery.send(replyId)).thenReturn(null);

    mvc.perform(post("/api/v1/meta/comments/replies/{replyId}/send", replyId))
        .andExpect(status().isOk());

    verify(delivery).send(replyId);
  }

  @Test
  void returnsForbiddenWhenCommentRepliesAreDisabled() throws Exception {
    when(delivery.send(replyId)).thenThrow(new MetaCommentReplyDisabledException());

    mvc.perform(post("/api/v1/meta/comments/replies/{replyId}/send", replyId))
        .andExpect(status().isForbidden());

    verify(delivery).send(replyId);
  }

  @Test
  void returnsBadRequestWhenReplyHasNotBeenApproved() throws Exception {
    when(delivery.send(replyId))
        .thenThrow(new IllegalStateException("Reply requires human approval before provider send"));

    mvc.perform(post("/api/v1/meta/comments/replies/{replyId}/send", replyId))
        .andExpect(status().isBadRequest());

    verify(delivery).send(replyId);
  }

  @Test
  void returnsNotFoundWhenReplyDoesNotExist() throws Exception {
    when(delivery.send(replyId)).thenThrow(new IllegalArgumentException("Comment reply not found"));

    mvc.perform(post("/api/v1/meta/comments/replies/{replyId}/send", replyId))
        .andExpect(status().isNotFound());

    verify(delivery).send(replyId);
  }
}
