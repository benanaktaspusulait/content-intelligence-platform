package com.pompom.creative.evidence;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

public record VisualEvidenceSubmissionDto(
    long validationRecordId,
    Long contentId,
    Long promptVersionId,
    String promptSha256,
    String gate,
    String status,
    UUID evidenceSetId,
    UUID renderJobId,
    UUID renderAssetId,
    String assetType,
    String assetRelativePath,
    String assetSha256,
    Map<String, Object> provenance,
    String reason,
    String verificationId,
    Instant verifiedAt,
    String submissionKey) {}
