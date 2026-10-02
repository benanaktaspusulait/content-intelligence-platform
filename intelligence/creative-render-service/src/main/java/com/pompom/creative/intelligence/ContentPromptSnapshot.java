package com.pompom.creative.intelligence;

public record ContentPromptSnapshot(
    String contractVersion,
    long contentId,
    String contentTitle,
    String contentType,
    String contentStatus,
    long promptVersionId,
    int promptVersionNumber,
    String promptText,
    String parsedIr,
    String promptSha256) {}
