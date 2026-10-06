package com.pompomhills.intelligence.quality;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.HexFormat;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.json.JsonMapper;

/**
 * Converts a {@link QualityReportDto} to and from the JSON snapshot stored on {@link
 * QualityValidationEntity}, and computes the prompt fingerprint used to find the latest analysis of
 * an unlinked prompt. Snapshot failures never fail a validation: the summary columns are still
 * saved and the report is simply not restorable later.
 */
final class QualityReportSnapshots {

  private static final Logger log = LoggerFactory.getLogger(QualityReportSnapshots.class);

  private static final JsonMapper MAPPER =
      JsonMapper.builder().disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();

  private QualityReportSnapshots() {}

  /** Returns the report as JSON, or null if it cannot be serialised. */
  static String toJson(QualityReportDto report) {
    try {
      return MAPPER.writeValueAsString(report);
    } catch (JacksonException e) {
      log.warn("Quality report snapshot could not be serialised; it will not be restorable", e);
      return null;
    }
  }

  /** Returns the stored report, or null if the snapshot is missing or unreadable. */
  static QualityReportDto fromJson(String json) {
    if (json == null || json.isBlank()) {
      return null;
    }
    try {
      return MAPPER.readValue(json, QualityReportDto.class);
    } catch (JacksonException e) {
      log.warn("Stored quality report snapshot could not be read", e);
      return null;
    }
  }

  static Map<String, Object> preRenderAssessment(String json) {
    if (json == null || json.isBlank()) return null;
    try {
      Map<?, ?> root = new com.fasterxml.jackson.databind.ObjectMapper().readValue(json, Map.class);
      Object assessment = root.get("preRenderAssessment");
      if (!(assessment instanceof Map<?, ?> map)) return null;
      @SuppressWarnings("unchecked")
      Map<String, Object> typed = (Map<String, Object>) map;
      return typed;
    } catch (Exception error) {
      log.warn("Stored pre-render assessment could not be read", error);
      return null;
    }
  }

  /** SHA-256 (lowercase hex) of the UTF-8 prompt text, or null for null input. */
  static String fingerprint(String prompt) {
    if (prompt == null) {
      return null;
    }
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(prompt.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException("SHA-256 is not available", e);
    }
  }
}
