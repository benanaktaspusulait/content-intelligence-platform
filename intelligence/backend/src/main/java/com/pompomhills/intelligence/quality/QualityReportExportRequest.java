package com.pompomhills.intelligence.quality;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * Payload for the backend PDF export of a quality report.
 *
 * <p>The report is posted back as-is (the same shape the validate endpoints return) so linked and
 * ad hoc validations share one export path. Nothing here is persisted or trusted for authorization;
 * it only drives document rendering.
 *
 * @param report the quality report currently displayed to the user
 * @param title optional content title shown in the PDF header
 * @param validationRecordId optional evidence record id (only present for linked validations)
 * @param timelineChartPng optional PNG snapshot of the timeline chart, base64 encoded (a {@code
 *     data:image/png;base64,} prefix is accepted)
 */
public record QualityReportExportRequest(
    @NotNull QualityReportDto report,
    @Size(max = 200) String title,
    Long validationRecordId,
    @Size(max = 8_000_000) String timelineChartPng) {}
