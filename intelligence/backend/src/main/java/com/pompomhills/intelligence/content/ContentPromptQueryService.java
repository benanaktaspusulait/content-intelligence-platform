package com.pompomhills.intelligence.content;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ContentPromptQueryService {
  private final PromptVersionRepository promptVersions;

  public ContentPromptQueryService(PromptVersionRepository promptVersions) {
    this.promptVersions = promptVersions;
  }

  @Transactional(readOnly = true)
  public ContentPromptSnapshot load(long contentId, long promptVersionId) {
    PromptVersionEntity prompt =
        promptVersions
            .findByIdAndContentId(promptVersionId, contentId)
            .orElseThrow(() -> new ContentPromptNotFoundException(contentId, promptVersionId));
    ContentEntity content = prompt.getContent();
    return new ContentPromptSnapshot(
        "v1",
        content.getId(),
        content.getTitle(),
        content.getContentType().name(),
        content.getStatus().name(),
        prompt.getId(),
        prompt.getVersionNumber(),
        prompt.getRawText(),
        prompt.getParsedIr(),
        sha256(prompt.getRawText()));
  }

  private String sha256(String promptText) {
    try {
      MessageDigest digest = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(digest.digest(promptText.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    }
  }
}
