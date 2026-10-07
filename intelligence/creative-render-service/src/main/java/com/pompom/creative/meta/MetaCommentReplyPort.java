package com.pompom.creative.meta;

import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.oauth.PlatformType;

/** Provider-independent public comment reply port. */
public interface MetaCommentReplyPort {

  PlatformType platform();

  SendResult sendApprovedReply(MetaCommentReply reply);

  record SendResult(boolean success, String providerReplyId, String message) {
    public static SendResult success(String providerReplyId) {
      return new SendResult(true, providerReplyId, "sent");
    }

    public static SendResult failure(String message) {
      return new SendResult(false, null, message);
    }
  }
}
