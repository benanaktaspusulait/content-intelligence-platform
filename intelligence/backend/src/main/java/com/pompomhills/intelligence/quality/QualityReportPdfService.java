package com.pompomhills.intelligence.quality;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;
import org.openpdf.text.Chunk;
import org.openpdf.text.Document;
import org.openpdf.text.DocumentException;
import org.openpdf.text.Element;
import org.openpdf.text.Font;
import org.openpdf.text.Image;
import org.openpdf.text.PageSize;
import org.openpdf.text.Paragraph;
import org.openpdf.text.Phrase;
import org.openpdf.text.Rectangle;
import org.openpdf.text.pdf.BaseFont;
import org.openpdf.text.pdf.ColumnText;
import org.openpdf.text.pdf.PdfContentByte;
import org.openpdf.text.pdf.PdfPCell;
import org.openpdf.text.pdf.PdfPCellEvent;
import org.openpdf.text.pdf.PdfPTable;
import org.openpdf.text.pdf.PdfPageEventHelper;
import org.openpdf.text.pdf.PdfWriter;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

/**
 * Renders a {@link QualityReportDto} into a PDF document entirely on the backend.
 *
 * <p>The layout mirrors the quality detail page: score card, pre-render readiness, priority fixes,
 * evaluation coverage, validation evidence, failed rules, family score bars, the timeline chart
 * (as a PNG snapshot supplied by the client) and the beat / state / consequence breakdown. DejaVu
 * Sans is embedded so non-ASCII content (for example Turkish characters) renders correctly.
 */
@Service
public class QualityReportPdfService {

  private static final String REGULAR_FONT = "fonts/DejaVuSans.ttf";
  private static final String BOLD_FONT = "fonts/DejaVuSans-Bold.ttf";
  private static final byte[] PNG_SIGNATURE = {(byte) 0x89, 'P', 'N', 'G'};
  private static final Pattern UNSUPPORTED_CHARS =
      Pattern.compile("[\\x{10000}-\\x{10FFFF}\\uFE0F\\u200D\\p{Cc}&&[^\\n\\t]]");
  private static final DateTimeFormatter TIMESTAMP =
      DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm z", Locale.ENGLISH);

  private static final Color INK = new Color(0x2c, 0x3e, 0x50);
  private static final Color MUTED = new Color(0x6c, 0x75, 0x7d);
  private static final Color BORDER = new Color(0xde, 0xe2, 0xe6);
  private static final Color SURFACE = new Color(0xf8, 0xf9, 0xfa);
  private static final Color GREEN = new Color(0x28, 0xa7, 0x45);
  private static final Color BLUE = new Color(0x00, 0x7b, 0xff);
  private static final Color AMBER = new Color(0xd3, 0x9e, 0x00);
  private static final Color RED = new Color(0xdc, 0x35, 0x45);
  private static final Color ORANGE = new Color(0xfd, 0x7e, 0x14);

  private final byte[] regularFontBytes;
  private final byte[] boldFontBytes;

  public QualityReportPdfService() {
    this.regularFontBytes = readResource(REGULAR_FONT);
    this.boldFontBytes = readResource(BOLD_FONT);
  }

  /** Renders the report and returns the PDF bytes. */
  public byte[] render(QualityReportExportRequest request) {
    QualityReportDto report = request.report();
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    Document document = new Document(PageSize.A4, 36, 36, 40, 50);
    try {
      PdfWriter writer = PdfWriter.getInstance(document, out);
      Fonts fonts = createFonts();
      writer.setPageEvent(new FooterEvent(fonts.small));
      document.addTitle(clean(titleOf(request)) + " - Quality Report");
      document.addCreator("Pompom Creative Intelligence");
      document.open();

      addHeader(document, request, report, fonts);
      addScoreCard(document, report, fonts);
      addPreRenderAssessment(document, report, fonts);
      addPriorityFixes(document, report, fonts);
      addEvaluationCoverage(document, report, fonts);
      addValidationEvidence(document, report, fonts);
      addFailedRules(document, report, fonts);
      addFamilyScores(document, report, fonts);
      addTimeline(document, request, report, fonts);
    } catch (IOException | RuntimeException e) {
      throw new QualityReportPdfException("Quality report PDF could not be rendered", e);
    } finally {
      if (document.isOpen()) {
        document.close();
      }
    }
    return out.toByteArray();
  }

  // ===== Sections =====

  private void addHeader(
      Document document, QualityReportExportRequest request, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    Paragraph eyebrow = new Paragraph("ANALYSIS REPORT", fonts.eyebrow);
    document.add(eyebrow);
    Paragraph title = new Paragraph(clean(titleOf(request)), fonts.title);
    title.setSpacingAfter(2);
    document.add(title);

    List<String> meta = new ArrayList<>();
    meta.add("Generated " + ZonedDateTime.now(ZoneId.systemDefault()).format(TIMESTAMP));
    if (notBlank(report.rulesetVersion())) {
      meta.add("Ruleset v" + report.rulesetVersion());
    }
    if (request.validationRecordId() != null) {
      meta.add("Evidence record #" + request.validationRecordId());
    }
    Paragraph metaLine = new Paragraph(String.join("  ·  ", meta), fonts.muted);
    metaLine.setSpacingAfter(10);
    document.add(metaLine);
  }

  private void addScoreCard(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    Color statusColor = statusColor(report.status());
    PdfPTable table = new PdfPTable(new float[] {34, 66});
    table.setWidthPercentage(100);
    table.setSpacingAfter(6);

    Paragraph score = new Paragraph();
    score.add(new Chunk(scoreText(report.overallScore()), fonts.scoreBig(statusColor)));
    score.add(new Chunk(" /100", fonts.muted));
    PdfPCell scoreCell = plainCell(SURFACE, 12);
    scoreCell.addElement(score);
    if (report.scoreCard() != null && notBlank(report.scoreCard().label())) {
      scoreCell.addElement(new Paragraph(clean(report.scoreCard().label()), fonts.bold));
    }
    Paragraph status = new Paragraph(clean(orDash(report.status())), fonts.colored(fonts.bold, statusColor));
    status.setSpacingBefore(4);
    scoreCell.addElement(status);
    table.addCell(scoreCell);

    PdfPTable counts = new PdfPTable(3);
    counts.setWidthPercentage(100);
    counts.addCell(countCell("Blockers", report.blockerCount(), RED, fonts));
    counts.addCell(countCell("Critical", report.criticalCount(), ORANGE, fonts));
    counts.addCell(countCell("Warnings", report.warningCount(), AMBER, fonts));
    PdfPCell countsCell = plainCell(SURFACE, 12);
    countsCell.setVerticalAlignment(Element.ALIGN_MIDDLE);
    countsCell.addElement(counts);
    table.addCell(countsCell);
    document.add(table);
  }

  private void addPreRenderAssessment(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    Map<String, Object> assessment = report.preRenderAssessment();
    if (assessment == null || assessment.isEmpty()) {
      return;
    }
    section(document, "Pre-render creative readiness", fonts);

    String grade = str(assessment.get("grade"));
    String readiness = str(assessment.get("readiness")).replace('_', ' ');
    String coverage = str(assessment.get("assessment_coverage_percent"));
    List<String> summary = new ArrayList<>();
    if (!grade.isEmpty()) {
      summary.add("Grade " + grade);
    }
    if (!readiness.isEmpty()) {
      summary.add(readiness);
    }
    if (!coverage.isEmpty()) {
      summary.add(coverage + "% evidence coverage");
    }
    if (!summary.isEmpty()) {
      document.add(new Paragraph(clean(String.join("  ·  ", summary)), fonts.bold));
    }
    String verdict = str(assessment.get("verdict"));
    if (!verdict.isEmpty()) {
      Paragraph p = new Paragraph(clean(verdict), fonts.body);
      p.setSpacingBefore(3);
      p.setSpacingAfter(6);
      document.add(p);
    }

    PdfPTable columns = new PdfPTable(3);
    columns.setWidthPercentage(100);
    columns.setSpacingAfter(6);
    columns.addCell(bulletColumn("Strengths", "✓", strings(assessment.get("strengths")), GREEN, fonts));
    columns.addCell(bulletColumn("Needs attention", "⚠", strings(assessment.get("concerns")), AMBER, fonts));
    columns.addCell(
        bulletColumn(
            "Recommended changes", "→", strings(assessment.get("recommended_changes")), BLUE, fonts));
    document.add(columns);

    Object aggregationObject = assessment.get("aggregation");
    if (aggregationObject instanceof Map<?, ?> aggregation) {
      Paragraph aggregationHeading = new Paragraph("Evaluation aggregation", fonts.bold);
      aggregationHeading.setSpacingBefore(4);
      aggregationHeading.setSpacingAfter(4);
      document.add(aggregationHeading);
      document.add(
          new Paragraph(
              "Score: "
                  + orDash(str(aggregation.get("score")))
                  + "  ·  Scored: "
                  + orDash(str(aggregation.get("scoredCount")))
                  + "  ·  Denominator: "
                  + orDash(str(aggregation.get("denominator")))
                  + "  ·  Evaluation coverage: "
                  + formatRatioPercent(aggregation.get("evaluationCoverage"))
                  + "  ·  State: "
                  + orDash(str(aggregation.get("aggregationState"))),
              fonts.body));
      document.add(
          new Paragraph(
              "PASS: "
                  + orDash(str(aggregation.get("passCount")))
                  + "  ·  FAIL: "
                  + orDash(str(aggregation.get("failCount")))
                  + "  ·  UNKNOWN: "
                  + orDash(str(aggregation.get("unknownCount")))
                  + "  ·  NOT EVALUATED: "
                  + orDash(str(aggregation.get("notEvaluatedCount")))
                  + "  ·  NOT APPLICABLE: "
                  + orDash(str(aggregation.get("notApplicableCount")))
                  + "  ·  SERVICE ERRORS: "
                  + orDash(str(aggregation.get("serviceErrorCount"))),
              fonts.muted));
    }

    Object family8Object = assessment.get("family8");
    if (family8Object instanceof Map<?, ?> family8) {
      Paragraph family8Heading = new Paragraph("Creative quality / Evidence completeness / Render authorization", fonts.bold);
      family8Heading.setSpacingBefore(6);
      family8Heading.setSpacingAfter(4);
      document.add(family8Heading);
      Map<?, ?> creative = family8.get("creativeQuality") instanceof Map<?, ?> map ? map : Map.of();
      Map<?, ?> evidence = family8.get("evidenceCompleteness") instanceof Map<?, ?> map ? map : Map.of();
      Map<?, ?> authorization = family8.get("renderAuthorization") instanceof Map<?, ?> map ? map : Map.of();
      document.add(
          new Paragraph(
              "Creative quality: score "
                  + orDash(str(creative.get("creativeScore")))
                  + " · grade "
                  + orDash(str(creative.get("creativeGrade"))),
              fonts.body));
      document.add(
          new Paragraph(
              "Evidence completeness: "
                  + orDash(str(evidence.get("status")))
                  + " · coverage "
                  + formatRatioPercent(evidence.get("evaluationCoverage")),
              fonts.body));
      document.add(
          new Paragraph(
              "Render authorization: " + orDash(str(authorization.get("status"))), fonts.body));
      if (authorization.get("reasons") instanceof List<?> reasons) {
        for (Object reason : reasons) {
          if (reason instanceof Map<?, ?> detail) {
            document.add(
                new Paragraph(
                    "Authorization reason: code "
                        + orDash(str(detail.get("code")))
                        + " · source "
                        + orDash(str(detail.get("source")))
                        + " · message "
                        + orDash(str(detail.get("message")))
                        + " · references "
                        + orDash(referenceText(detail.get("references"), detail.get("evidenceReferences"))),
                    fonts.muted));
          }
        }
      }
    }

    List<Map.Entry<?, ?>> applicabilityRows = new ArrayList<>();
    if (assessment.get("specialized_applicability") instanceof Map<?, ?> applicability) {
      for (Map.Entry<?, ?> entry : applicability.entrySet()) {
        if (entry.getValue() instanceof Map<?, ?>) {
          applicabilityRows.add(entry);
        }
      }
    }
    if (!applicabilityRows.isEmpty()) {
      applicabilityRows.sort(
          (left, right) -> str(left.getKey()).compareTo(str(right.getKey())));
      Paragraph applicabilityHeading = new Paragraph("Specialized applicability", fonts.bold);
      applicabilityHeading.setSpacingBefore(4);
      applicabilityHeading.setSpacingAfter(4);
      document.add(applicabilityHeading);

      PdfPTable table = new PdfPTable(new float[] {30, 18, 12, 28, 12});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      table.setSpacingAfter(6);
      compactHeader(table, fonts, "Rule", "Applicability", "Confidence", "Reason", "Evidence");
      for (Map.Entry<?, ?> entry : applicabilityRows) {
        Map<?, ?> detail = (Map<?, ?>) entry.getValue();
        table.addCell(cell(orDash(str(entry.getKey())), fonts.small, null));
        table.addCell(cell(orDash(str(detail.get("status"))), fonts.small, null));
        table.addCell(cell(orDash(str(detail.get("confidence"))), fonts.small, null));
        table.addCell(cell(orDash(str(detail.get("reason"))), fonts.small, null));
        table.addCell(cell(orDash(applicabilityEvidence(detail)), fonts.small, null));
      }
      document.add(table);
    }

    List<Map<?, ?>> dimensions = maps(assessment.get("dimensions"));
    if (!dimensions.isEmpty()) {
      PdfPTable table = new PdfPTable(new float[] {24, 16, 60});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      header(table, fonts, "Dimension", "Status", "Assessment");
      for (Map<?, ?> dimension : dimensions) {
        String dimensionStatus = str(dimension.get("status"));
        boolean attention = "NEEDS_ATTENTION".equals(dimensionStatus);
        table.addCell(cell(str(dimension.get("title")), fonts.bold, null));
        table.addCell(
            cell(
                dimensionStatus.replace('_', ' '),
                fonts.colored(fonts.small, attention ? AMBER : GREEN),
                null));
        PdfPCell detail = cell("", fonts.body, null);
        detail.setPhrase(null);
        detail.addElement(new Paragraph(clean(str(dimension.get("summary"))), fonts.body));
        String observed = str(dimension.get("observed"));
        if (!observed.isEmpty()) {
          detail.addElement(new Paragraph(clean(observed), fonts.muted));
        }
        String recommendation = str(dimension.get("recommendation"));
        if (attention && !recommendation.isEmpty()) {
          detail.addElement(
              new Paragraph("What to change: " + clean(recommendation), fonts.small));
        }
        table.addCell(detail);
      }
      document.add(table);
    }
  }

  private void addPriorityFixes(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    List<PriorityFixDto> fixes = orEmpty(report.priorityFixes());
    if (fixes.isEmpty()) {
      return;
    }
    section(document, "Priority fixes (" + fixes.size() + ")", fonts);
    int index = 1;
    for (PriorityFixDto fix : fixes) {
      PdfPTable table = new PdfPTable(1);
      table.setWidthPercentage(100);
      table.setSpacingAfter(5);
      table.setKeepTogether(true);
      PdfPCell cell = plainCell(SURFACE, 8);
      cell.setBorderColor(BORDER);
      cell.setBorderWidth(0.5f);

      Paragraph head = new Paragraph();
      head.add(new Chunk("#" + index++ + "  ", fonts.bold));
      head.add(new Chunk(clean(orDash(fix.severity())) + "  ", fonts.colored(fonts.bold, severityColor(fix.severity()))));
      head.add(new Chunk(clean(orDash(fix.ruleName())), fonts.bold));
      head.add(new Chunk("   " + clean(orDash(fix.family())), fonts.muted));
      cell.addElement(head);
      cell.addElement(labelled("Issue: ", fix.issue(), fonts));
      cell.addElement(labelled("Fix: ", fix.recommendation(), fonts));
      cell.addElement(
          new Paragraph(
              clean(orDash(fix.strategy())) + "  ·  Impact: " + clean(orDash(fix.impact())),
              fonts.muted));
      table.addCell(cell);
      document.add(table);
    }
  }

  private void addEvaluationCoverage(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    List<RuleEvaluationDto> passed = orEmpty(report.passedRules());
    List<RuleEvaluationDto> failed = orEmpty(report.failedRules());
    List<RuleEvaluationDto> errors = orEmpty(report.serviceErrors());
    List<RuleEvaluationDto> unknown = orEmpty(report.unknownRules());
    List<RuleEvaluationDto> notApplicable = orEmpty(report.notApplicableRules());
    if (passed.isEmpty()
        && failed.isEmpty()
        && errors.isEmpty()
        && unknown.isEmpty()
        && notApplicable.isEmpty()) {
      return;
    }
    section(document, "Rule outcome coverage", fonts);
    document.add(
        new Paragraph(
            "PASS: "
                + passed.size()
                + "   ·   FAIL: "
                + failed.size()
                + "   ·   UNKNOWN: "
                + unknown.size()
                + "   ·   NOT APPLICABLE: "
                + notApplicable.size()
                + "   ·   SERVICE ERROR: "
                + errors.size(),
            fonts.body));
    for (RuleEvaluationDto rule : passed) {
      document.add(outcomeLine("PASS", rule, fonts));
    }
    for (RuleEvaluationDto rule : unknown) {
      document.add(outcomeLine("UNKNOWN", rule, fonts));
    }
    for (RuleEvaluationDto rule : notApplicable) {
      document.add(outcomeLine("NOT APPLICABLE", rule, fonts));
    }
    for (RuleEvaluationDto rule : errors) {
      document.add(outcomeLine("SERVICE ERROR", rule, fonts));
    }
  }

  private void addValidationEvidence(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    section(document, "Validation evidence", fonts);
    document.add(
        labelled("Parser confidence: ", Math.round(report.parserConfidence() * 100) + "%", fonts));
    if (report.canonicalEvidenceConfidence() != null) {
      document.add(
          labelled(
              "Canonical evidence confidence: ",
              Math.round(report.canonicalEvidenceConfidence() * 100) + "%",
              fonts));
    }
    QualityProvenanceDto provenance = report.provenance();
    if (provenance != null) {
      document.add(labelled("Stage: ", provenance.evaluationStage(), fonts));
      document.add(
          labelled(
              "Semantic model: ",
              orDash(provenance.semanticProvider()) + " / " + orDash(provenance.semanticModelVersion()),
              fonts));
      document.add(
          labelled(
              "Versions: ",
              "parser " + orDash(provenance.parserVersion()) + ", rule engine "
                  + orDash(provenance.ruleEngineVersion()),
              fonts));
    }
    if (!orEmpty(report.evidenceMissing()).isEmpty()) {
      document.add(labelled("Missing evidence: ", String.join(", ", report.evidenceMissing()), fonts));
    }
    if (!orEmpty(report.parserWarnings()).isEmpty()) {
      document.add(labelled("Parser warnings: ", String.join(" · ", report.parserWarnings()), fonts));
    }
    if (!orEmpty(report.parserAssumptions()).isEmpty()) {
      document.add(
          labelled("Parser assumptions: ", String.join(" · ", report.parserAssumptions()), fonts));
    }
  }

  private void addFailedRules(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    List<RuleEvaluationDto> failed = orEmpty(report.failedRules());
    if (failed.isEmpty()) {
      return;
    }
    section(document, "Failed rules (" + failed.size() + ")", fonts);
    PdfPTable table = new PdfPTable(new float[] {12, 13, 13, 36, 11, 15});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    header(table, fonts, "Severity", "Rule", "Family", "Message", "Actual", "Threshold");
    for (RuleEvaluationDto rule : failed) {
      table.addCell(cell(orDash(rule.severity()), fonts.colored(fonts.small, severityColor(rule.severity())), null));
      table.addCell(cell(orDash(rule.ruleId()), fonts.small, null));
      table.addCell(cell(orDash(rule.family()), fonts.small, null));
      table.addCell(cell(orDash(rule.message()), fonts.small, null));
      table.addCell(cell(number(rule.actualValue()), fonts.small, null));
      table.addCell(cell(number(rule.thresholdValue()), fonts.small, null));
    }
    document.add(table);
  }

  private void addFamilyScores(Document document, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    Map<String, Double> scores = report.familyScores();
    if (scores == null || scores.isEmpty()) {
      return;
    }
    section(document, "Quality family scores", fonts);
    PdfPTable table = new PdfPTable(new float[] {32, 58, 10});
    table.setWidthPercentage(100);
    scores.entrySet().stream()
        .sorted(
            (left, right) -> {
              Double leftValue = left.getValue();
              Double rightValue = right.getValue();
              if (leftValue == null && rightValue == null) {
                return String.valueOf(left.getKey()).compareTo(String.valueOf(right.getKey()));
              }
              if (leftValue == null) {
                return 1;
              }
              if (rightValue == null) {
                return -1;
              }
              return Double.compare(rightValue, leftValue);
            })
        .forEach(
            entry -> {
              Double value = entry.getValue();
              PdfPCell name = plainCell(null, 4);
              name.setPhrase(new Phrase(clean(entry.getKey()), fonts.body));
              name.setVerticalAlignment(Element.ALIGN_MIDDLE);
              table.addCell(name);

              PdfPCell bar = plainCell(null, 4);
              bar.setFixedHeight(16);
              if (value != null) {
                bar.setCellEvent(new BarEvent(value, familyScoreColor(value)));
              }
              table.addCell(bar);

              PdfPCell number = plainCell(null, 4);
              number.setPhrase(
                  new Phrase(
                      value == null
                          ? "N/A"
                          : String.format(Locale.ROOT, "%.0f", value),
                      fonts.bold));
              number.setHorizontalAlignment(Element.ALIGN_RIGHT);
              number.setVerticalAlignment(Element.ALIGN_MIDDLE);
              table.addCell(number);
            });
    document.add(table);
  }

  private void addTimeline(
      Document document, QualityReportExportRequest request, QualityReportDto report, Fonts fonts)
      throws DocumentException {
    TimelineDataDto timeline = report.timelineData();
    if (timeline == null) {
      return;
    }
    List<BeatDto> beats = orEmpty(timeline.beats());
    List<StateSegmentDto> segments = orEmpty(timeline.stateSegments());
    List<ConsequenceMarkerDto> markers = orEmpty(timeline.consequenceMarkers());

    section(document, "Timeline visualization", fonts);
    Image chart = decodeChart(request.timelineChartPng());
    if (chart != null) {
      chart.scaleToFit(document.right() - document.left(), 240);
      chart.setAlignment(Element.ALIGN_CENTER);
      document.add(chart);
    } else {
      document.add(new Paragraph("Timeline chart snapshot was not provided.", fonts.muted));
    }

    if (!beats.isEmpty()) {
      double duration = beats.stream().mapToDouble(BeatDto::endTime).max().orElse(0);
      double avgIntensity = beats.stream().mapToInt(BeatDto::intensity).average().orElse(0);
      long newConsequences = beats.stream().filter(BeatDto::isNewConsequence).count();
      Paragraph stats =
          new Paragraph(
              "Duration "
                  + oneDecimal(duration)
                  + "s   ·   Beats "
                  + beats.size()
                  + "   ·   New consequences "
                  + newConsequences
                  + "   ·   Avg intensity "
                  + oneDecimal(avgIntensity)
                  + "/10",
              fonts.muted);
      stats.setSpacingBefore(4);
      document.add(stats);

      section(document, "Timeline overview (" + beats.size() + " beats)", fonts);
      PdfPTable table = new PdfPTable(new float[] {14, 32, 42, 12});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      header(table, fonts, "Time", "Action", "Consequence", "Intensity");
      for (BeatDto beat : beats) {
        table.addCell(cell(oneDecimal(beat.startTime()) + "s - " + oneDecimal(beat.endTime()) + "s", fonts.small, null));
        table.addCell(cell(orDash(beat.action()), fonts.small, null));
        String consequence = (beat.isNewConsequence() ? "NEW  " : "") + orDash(beat.consequence());
        table.addCell(cell(consequence, fonts.small, null));
        table.addCell(
            cell(
                beat.intensity() + "/10",
                fonts.colored(fonts.bold, intensityColor(beat.intensity())),
                null));
      }
      document.add(table);
    }

    if (!segments.isEmpty()) {
      Paragraph heading = new Paragraph("Visual state distribution", fonts.bold);
      heading.setSpacingBefore(10);
      heading.setSpacingAfter(4);
      document.add(heading);
      PdfPTable table = new PdfPTable(new float[] {40, 30, 30});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      header(table, fonts, "State", "Range", "Share");
      for (StateSegmentDto segment : segments) {
        boolean dominant = isDominantStateShare(segment.percentage());
        table.addCell(cell(orDash(segment.stateId()), fonts.small, null));
        table.addCell(
            cell(oneDecimal(segment.startTime()) + "s - " + oneDecimal(segment.endTime()) + "s", fonts.small, null));
        table.addCell(
            cell(
                formatStateShare(segment.percentage()) + (dominant ? "  (above 30%)" : ""),
                fonts.colored(dominant ? fonts.bold : fonts.small, dominant ? RED : INK),
                null));
      }
      document.add(table);
    }

    if (!markers.isEmpty()) {
      Paragraph heading = new Paragraph("Consequence markers", fonts.bold);
      heading.setSpacingBefore(10);
      heading.setSpacingAfter(4);
      document.add(heading);
      PdfPTable table = new PdfPTable(new float[] {14, 68, 18});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      header(table, fonts, "Time", "Consequence", "Type");
      for (ConsequenceMarkerDto marker : markers) {
        table.addCell(cell(oneDecimal(marker.time()) + "s", fonts.small, null));
        table.addCell(cell(orDash(marker.consequence()), fonts.small, null));
        table.addCell(cell(orDash(marker.type()), fonts.small, null));
      }
      document.add(table);
    }
  }

  // ===== Building blocks =====

  private void section(Document document, String text, Fonts fonts) throws DocumentException {
    Paragraph heading = new Paragraph(clean(text), fonts.heading);
    heading.setSpacingBefore(14);
    heading.setSpacingAfter(5);
    heading.setKeepTogether(true);
    document.add(heading);
    PdfPTable rule = new PdfPTable(1);
    rule.setWidthPercentage(100);
    PdfPCell line = new PdfPCell();
    line.setFixedHeight(1);
    line.setBorder(Rectangle.BOTTOM);
    line.setBorderColor(BORDER);
    rule.addCell(line);
    rule.setSpacingAfter(2);
    document.add(rule);
  }

  private PdfPCell plainCell(Color background, float padding) {
    PdfPCell cell = new PdfPCell();
    cell.setBorder(Rectangle.NO_BORDER);
    cell.setPadding(padding);
    if (background != null) {
      cell.setBackgroundColor(background);
    }
    return cell;
  }

  private PdfPCell cell(String text, Font font, Color background) {
    PdfPCell cell = new PdfPCell(new Phrase(clean(text), font));
    cell.setPadding(5);
    cell.setBorderColor(BORDER);
    cell.setBorderWidth(0.5f);
    if (background != null) {
      cell.setBackgroundColor(background);
    }
    return cell;
  }

  private void header(PdfPTable table, Fonts fonts, String... labels) {
    for (String label : labels) {
      PdfPCell cell = cell(label, fonts.colored(fonts.bold, Color.WHITE), INK);
      cell.setBorderColor(INK);
      table.addCell(cell);
    }
  }

  private void compactHeader(PdfPTable table, Fonts fonts, String... labels) {
    for (String label : labels) {
      PdfPCell cell = cell(label, fonts.colored(fonts.small, Color.WHITE), INK);
      cell.setBorderColor(INK);
      table.addCell(cell);
    }
  }

  private PdfPCell countCell(String label, int count, Color color, Fonts fonts) {
    PdfPCell cell = plainCell(null, 2);
    cell.setHorizontalAlignment(Element.ALIGN_CENTER);
    Paragraph number = new Paragraph(String.valueOf(count), fonts.colored(fonts.countBig, color));
    number.setAlignment(Element.ALIGN_CENTER);
    Paragraph caption = new Paragraph(label, fonts.muted);
    caption.setAlignment(Element.ALIGN_CENTER);
    cell.addElement(number);
    cell.addElement(caption);
    return cell;
  }

  private PdfPCell bulletColumn(
      String heading, String bullet, List<String> items, Color color, Fonts fonts) {
    PdfPCell cell = plainCell(SURFACE, 7);
    cell.setBorderColor(Color.WHITE);
    cell.setBorderWidth(3);
    cell.setBorder(Rectangle.BOX);
    cell.addElement(new Paragraph(heading, fonts.bold));
    if (items.isEmpty()) {
      cell.addElement(new Paragraph("—", fonts.muted));
    }
    for (String item : items) {
      Paragraph p = new Paragraph();
      p.setSpacingBefore(2);
      p.add(new Chunk(bullet + " ", fonts.colored(fonts.bold, color)));
      p.add(new Chunk(clean(item), fonts.small));
      cell.addElement(p);
    }
    return cell;
  }

  private Paragraph labelled(String label, String value, Fonts fonts) {
    Paragraph paragraph = new Paragraph();
    paragraph.setSpacingBefore(2);
    paragraph.add(new Chunk(label, fonts.bold));
    paragraph.add(new Chunk(clean(orDash(value)), fonts.body));
    return paragraph;
  }

  private Paragraph outcomeLine(String outcome, RuleEvaluationDto rule, Fonts fonts) {
    Paragraph paragraph = new Paragraph();
    paragraph.setSpacingBefore(2);
    paragraph.add(new Chunk(clean(outcome), fonts.bold));
    paragraph.add(
        new Chunk(
            "  ·  "
                + clean(orDash(rule.ruleId()))
                + "  ·  "
                + clean(orDash(rule.message())),
            fonts.small));
    return paragraph;
  }

  private Paragraph ruleLine(RuleEvaluationDto rule, Fonts fonts) {
    Paragraph paragraph = new Paragraph();
    paragraph.setSpacingBefore(2);
    paragraph.add(new Chunk(clean(orDash(rule.ruleId())), fonts.bold));
    paragraph.add(new Chunk("  ·  " + clean(orDash(rule.message())), fonts.small));
    return paragraph;
  }

  private Image decodeChart(String encoded) {
    if (!notBlank(encoded)) {
      return null;
    }
    try {
      String payload = encoded.substring(encoded.indexOf(',') + 1).trim();
      byte[] bytes = Base64.getMimeDecoder().decode(payload);
      if (bytes.length < PNG_SIGNATURE.length) {
        return null;
      }
      for (int i = 0; i < PNG_SIGNATURE.length; i++) {
        if (bytes[i] != PNG_SIGNATURE[i]) {
          return null;
        }
      }
      return Image.getInstance(bytes);
    } catch (IllegalArgumentException | IOException e) {
      return null;
    }
  }

  // ===== Formatting helpers =====

  static boolean isDominantStateShare(double percentage) {
    return percentage > 30.0;
  }

  static String formatStateShare(double percentage) {
    return Math.round(Math.max(0.0, Math.min(100.0, percentage))) + "%";
  }

  private static String titleOf(QualityReportExportRequest request) {
    return notBlank(request.title()) ? request.title().trim() : "Pompom creative quality report";
  }

  private static String clean(String text) {
    return text == null ? "" : UNSUPPORTED_CHARS.matcher(text).replaceAll("");
  }

  private static boolean notBlank(String text) {
    return text != null && !text.isBlank();
  }

  private static String orDash(String text) {
    return notBlank(text) ? text : "—";
  }

  private static String oneDecimal(double value) {
    return String.format(Locale.ROOT, "%.1f", value);
  }

  private static String scoreText(Double value) {
    return value == null ? "N/A" : oneDecimal(value);
  }

  private static String formatRatioPercent(Object value) {
    if (value == null) {
      return "—";
    }
    double ratio;
    if (value instanceof Number number) {
      ratio = number.doubleValue();
    } else {
      try {
        ratio = Double.parseDouble(String.valueOf(value));
      } catch (NumberFormatException e) {
        return "—";
      }
    }
    if (!Double.isFinite(ratio)) {
      return "—";
    }
    return Math.round(Math.max(0.0, Math.min(1.0, ratio)) * 100.0) + "%";
  }

  private static String applicabilityEvidence(Map<?, ?> detail) {
    String canonical = evidenceText(detail.get("evidenceReferences"));
    return !canonical.isEmpty() ? canonical : evidenceText(detail.get("evidence"));
  }

  private static String referenceText(Object primary, Object fallback) {
    String references = evidenceText(primary);
    return !references.isEmpty() ? references : evidenceText(fallback);
  }

  private static String evidenceText(Object value) {
    if (value instanceof List<?> list) {
      List<String> references = new ArrayList<>();
      for (Object item : list) {
        if (item != null && !String.valueOf(item).isBlank()) {
          references.add(String.valueOf(item));
        }
      }
      return String.join(", ", references);
    }
    return str(value).trim();
  }

  private static String number(Double value) {
    if (value == null) {
      return "—";
    }
    return value == Math.rint(value)
        ? String.format(Locale.ROOT, "%.0f", value)
        : String.format(Locale.ROOT, "%.2f", value);
  }

  private static String str(Object value) {
    return value == null ? "" : String.valueOf(value);
  }

  private static List<String> strings(Object value) {
    List<String> result = new ArrayList<>();
    if (value instanceof List<?> list) {
      for (Object item : list) {
        if (item != null) {
          result.add(String.valueOf(item));
        }
      }
    }
    return result;
  }

  private static List<Map<?, ?>> maps(Object value) {
    List<Map<?, ?>> result = new ArrayList<>();
    if (value instanceof List<?> list) {
      for (Object item : list) {
        if (item instanceof Map<?, ?> map) {
          result.add(map);
        }
      }
    }
    return result;
  }

  private static <T> List<T> orEmpty(List<T> list) {
    return list == null ? List.of() : list;
  }

  private static Color statusColor(String status) {
    if ("RENDER_READY".equals(status)) {
      return GREEN;
    }
    if ("NEEDS_REVISION".equals(status)) {
      return AMBER;
    }
    return RED;
  }

  private static Color severityColor(String severity) {
    if ("BLOCKER".equals(severity) || "CRITICAL".equals(severity)) {
      return RED;
    }
    if ("WARNING".equals(severity)) {
      return AMBER;
    }
    return MUTED;
  }

  private static Color familyScoreColor(double score) {
    if (score >= 90) {
      return GREEN;
    }
    if (score >= 75) {
      return BLUE;
    }
    if (score >= 60) {
      return AMBER;
    }
    return RED;
  }

  private static Color intensityColor(int intensity) {
    if (intensity >= 8) {
      return RED;
    }
    if (intensity >= 6) {
      return ORANGE;
    }
    if (intensity >= 4) {
      return AMBER;
    }
    return GREEN;
  }

  private static byte[] readResource(String path) {
    try (InputStream in = new ClassPathResource(path).getInputStream()) {
      return in.readAllBytes();
    } catch (IOException e) {
      throw new IllegalStateException("Missing PDF font resource: " + path, e);
    }
  }

  private Fonts createFonts() throws DocumentException, IOException {
    BaseFont regular =
        BaseFont.createFont(
            "DejaVuSans.ttf", BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, regularFontBytes, null);
    BaseFont bold =
        BaseFont.createFont(
            "DejaVuSans-Bold.ttf", BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, boldFontBytes, null);
    return new Fonts(regular, bold);
  }

  // ===== Nested types =====

  /** Font set used across the document. */
  private static final class Fonts {
    final BaseFont regularBase;
    final BaseFont boldBase;
    final Font title;
    final Font eyebrow;
    final Font heading;
    final Font body;
    final Font small;
    final Font muted;
    final Font bold;
    final Font countBig;

    Fonts(BaseFont regular, BaseFont boldBase) {
      this.regularBase = regular;
      this.boldBase = boldBase;
      this.title = new Font(boldBase, 20, Font.NORMAL, INK);
      this.eyebrow = new Font(boldBase, 8, Font.NORMAL, MUTED);
      this.heading = new Font(boldBase, 13, Font.NORMAL, INK);
      this.body = new Font(regular, 9.5f, Font.NORMAL, INK);
      this.small = new Font(regular, 8.5f, Font.NORMAL, INK);
      this.muted = new Font(regular, 8.5f, Font.NORMAL, MUTED);
      this.bold = new Font(boldBase, 9.5f, Font.NORMAL, INK);
      this.countBig = new Font(boldBase, 20, Font.NORMAL, INK);
    }

    Font scoreBig(Color color) {
      return new Font(boldBase, 34, Font.NORMAL, color);
    }

    Font colored(Font base, Color color) {
      Font copy = new Font(base);
      copy.setColor(color);
      return copy;
    }
  }

  /** Draws a horizontal score bar (0-100) behind a table cell. */
  private static final class BarEvent implements PdfPCellEvent {
    private final double score;
    private final Color color;

    BarEvent(double score, Color color) {
      this.score = Math.max(0, Math.min(100, score));
      this.color = color;
    }

    @Override
    public void cellLayout(PdfPCell cell, Rectangle position, PdfContentByte[] canvases) {
      PdfContentByte canvas = canvases[PdfPTable.BACKGROUNDCANVAS];
      float height = 9;
      float x = position.getLeft() + 2;
      float width = position.getWidth() - 4;
      float y = position.getBottom() + (position.getHeight() - height) / 2;
      canvas.saveState();
      canvas.setColorFill(new Color(0xe9, 0xec, 0xef));
      canvas.rectangle(x, y, width, height);
      canvas.fill();
      canvas.setColorFill(color);
      canvas.rectangle(x, y, (float) (width * score / 100.0), height);
      canvas.fill();
      canvas.restoreState();
    }
  }

  /** Page footer with page number. */
  private static final class FooterEvent extends PdfPageEventHelper {
    private final Font font;

    FooterEvent(Font font) {
      this.font = font;
    }

    @Override
    public void onEndPage(PdfWriter writer, Document document) {
      Phrase footer =
          new Phrase(
              "Pompom Creative Intelligence  ·  Page " + writer.getPageNumber(), font);
      ColumnText.showTextAligned(
          writer.getDirectContent(),
          Element.ALIGN_CENTER,
          footer,
          (document.right() + document.left()) / 2,
          document.bottom() - 22,
          0);
    }
  }
}
