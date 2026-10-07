package com.pompom.creative.oauth;

/** Raised whenever a public Meta comment reply is attempted while replies are disabled. */
public class MetaCommentReplyDisabledException extends IllegalStateException {
  public MetaCommentReplyDisabledException() {
    super("Facebook and Instagram comment replies are disabled");
  }
}
