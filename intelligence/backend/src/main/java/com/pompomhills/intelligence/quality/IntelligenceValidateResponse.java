package com.pompomhills.intelligence.quality;

/**
 * Public validation response. {@code validationRecordId} is the ID evidence consumers pass to the
 * internal evidence endpoint.
 */
public record IntelligenceValidateResponse(long validationRecordId, QualityReportDto report) {}
