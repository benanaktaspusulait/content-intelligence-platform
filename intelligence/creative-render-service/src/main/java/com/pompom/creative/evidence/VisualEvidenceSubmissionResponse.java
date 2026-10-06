package com.pompom.creative.evidence;

import java.util.Map;

public record VisualEvidenceSubmissionResponse(
    long validationRecordId,
    long visualEvidenceId,
    String gate,
    String status,
    boolean firstFrameEligible,
    boolean finalVideoEligible,
    Map<String, Object> visualEvidence,
    boolean created) {}
