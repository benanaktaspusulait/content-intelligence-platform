package com.pompom.creative.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

import com.pompom.creative.api.controller.MetaCommentController;
import com.pompom.creative.meta.MetaCommentModerationService;
import com.pompom.creative.meta.MetaCommentReplyDeliveryService;
import com.pompom.creative.repository.MetaCommentRepository;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import java.util.List;
import org.junit.jupiter.api.Test;

class MetaCommentControllerReadTest {
  @Test
  void readEndpointsReturnNewestRowsAndStaySafeWithEmptyRepositories() {
    var comments = mock(MetaCommentRepository.class);
    var replies = mock(MetaCommentReplyRepository.class);
    when(comments.findTop100ByOrderByCreatedAtDesc()).thenReturn(List.of());
    when(replies.findTop100ByOrderByCreatedAtDesc()).thenReturn(List.of());
    var controller = new MetaCommentController(mock(MetaCommentModerationService.class), mock(MetaCommentReplyDeliveryService.class), mock(MetaCommentReconciliationService.class), comments, replies);
    assertThat(controller.list().getBody()).isEmpty();
    assertThat(controller.listReplies().getBody()).isEmpty();
    verify(comments).findTop100ByOrderByCreatedAtDesc();
    verify(replies).findTop100ByOrderByCreatedAtDesc();
  }

  @Test
  void reconciliationReportsUnavailableWhenCompatibilityControllerHasNoService() {
    var controller = new MetaCommentController(mock(MetaCommentModerationService.class), mock(MetaCommentReplyDeliveryService.class));
    assertThat(controller.reconcile(10).getStatusCode().value()).isEqualTo(503);
  }
}
