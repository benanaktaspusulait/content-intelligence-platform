package com.pompomhills.intelligence.quality;

/**
 * Identifies the prompt whose latest stored analysis should be returned.
 *
 * <p>When both {@code contentId} and {@code promptVersionId} are present the linked analysis for
 * that immutable prompt version is returned. Otherwise {@code prompt} is required and the latest
 * unlinked analysis of exactly that text is returned.
 */
public record LatestValidationRequest(String prompt, Long contentId, Long promptVersionId) {}
