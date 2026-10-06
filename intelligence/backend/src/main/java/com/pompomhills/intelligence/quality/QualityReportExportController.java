package com.pompomhills.intelligence.quality;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.Locale;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Generates a downloadable PDF for a quality report. Works for both linked (persisted) and ad hoc
 * validations because the report is posted back rather than looked up by id.
 */
@RestController
@RequestMapping("/api/v1/intelligence/quality")
@Tag(name = "Quality Report Export", description = "Backend-rendered PDF export of quality reports")
public class QualityReportExportController {

  private static final Logger log = LoggerFactory.getLogger(QualityReportExportController.class);

  private final QualityReportPdfService pdfService;

  public QualityReportExportController(QualityReportPdfService pdfService) {
    this.pdfService = pdfService;
  }

  @PostMapping("/report/export-pdf")
  @Operation(
      summary = "Export a quality report as PDF",
      description =
          "Renders the posted quality report (and optional timeline chart PNG snapshot) into a PDF "
              + "attachment on the backend.")
  public ResponseEntity<byte[]> exportPdf(@Valid @RequestBody QualityReportExportRequest request) {
    byte[] pdf = pdfService.render(request);
    ContentDisposition disposition =
        ContentDisposition.attachment().filename(fileName(request.title()), StandardCharsets.UTF_8).build();
    return ResponseEntity.ok()
        .contentType(MediaType.APPLICATION_PDF)
        .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
        .header(HttpHeaders.CACHE_CONTROL, "no-store")
        .contentLength(pdf.length)
        .body(pdf);
  }

  @ExceptionHandler(QualityReportPdfException.class)
  ResponseEntity<ProblemDetail> renderFailed(QualityReportPdfException error) {
    log.error("Quality report PDF rendering failed", error);
    ProblemDetail problem =
        ProblemDetail.forStatusAndDetail(
            HttpStatus.INTERNAL_SERVER_ERROR, "The quality report PDF could not be generated.");
    problem.setTitle("PDF export failed");
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .contentType(MediaType.APPLICATION_PROBLEM_JSON)
        .body(problem);
  }

  private static String fileName(String title) {
    String slug =
        Normalizer.normalize(title == null ? "" : title, Normalizer.Form.NFD)
            .replaceAll("\\p{M}", "")
            .toLowerCase(Locale.ROOT)
            .replaceAll("[^a-z0-9]+", "-")
            .replaceAll("^-+|-+$", "");
    if (slug.length() > 80) {
      slug = slug.substring(0, 80).replaceAll("-+$", "");
    }
    return slug.isEmpty() ? "quality-report.pdf" : slug + "-quality-report.pdf";
  }
}
