package com.pompomhills.intelligence.quality;

/** Raised when the quality report PDF cannot be rendered. */
public class QualityReportPdfException extends RuntimeException {

  public QualityReportPdfException(String message, Throwable cause) {
    super(message, cause);
  }
}
