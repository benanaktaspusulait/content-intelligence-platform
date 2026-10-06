package com.pompomhills.intelligence.quality;

import java.time.Instant;

/** A previously stored analysis, returned so the UI can show it without re-running validation. */
public record StoredValidationResponse(
    long validationRecordId, QualityReportDto report, Instant analyzedAt) {}
