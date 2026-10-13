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
 * evaluation coverage, validation evidence, failed rules, family score bars, the timeline chart (as
 * a PNG snapshot supplied by the client) and the beat / state / consequence breakdown. DejaVu Sans
 * is embedded so non-ASCII content (for example Turkish characters) renders correctly.
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

  /** Additive post-family snapshot export; historical Family report rendering is unchanged. */
  public byte[] renderWorkflow(Map<String, Object> snapshot) {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    Document document = new Document(PageSize.A4, 36, 36, 40, 50);
    try {
      PdfWriter writer = PdfWriter.getInstance(document, out);
      Fonts fonts = createFonts();
      writer.setPageEvent(new FooterEvent(fonts.small));
      document.addTitle("Pompom Hills - Production Review");
      document.open();
      addWorkflowHeader(document, snapshot, fonts);
      addWorkflowSummary(document, snapshot, fonts);
      addWorkflowDimensions(document, snapshot, fonts);
      addWorkflowEvidence(document, snapshot, fonts);
      addWorkflowBeats(document, snapshot, fonts);
      addWorkflowNextSteps(document, snapshot, fonts);
      } catch (IOException | RuntimeException e) {
      throw new QualityReportPdfException("Workflow PDF could not be rendered", e);
    } finally {
      if (document.isOpen()) document.close();
    }
    return out.toByteArray();
  }

  /** Full Step 5 analysis PDF: combines BUILD_PROMPT workflow + REVIEW (Step 5) analysis. */
  public byte[] renderFullAnalysis(Map<String, Object> workflow, Map<String, Object> review) {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    Document document = new Document(PageSize.A4, 36, 36, 40, 50);
    try {
      PdfWriter writer = PdfWriter.getInstance(document, out);
      Fonts fonts = createFonts();
      writer.setPageEvent(new FooterEvent(fonts.small));
      document.addTitle("Pompom Hills - Quality Analysis Report");
      document.addCreator("Pompom Creative Intelligence");
      document.open();

      // SECTION 1: Report Identity
      addFullAnalysisHeader(document, workflow, review, fonts);

      // SECTION 2: Executive Summary
      addFullAnalysisSummary(document, workflow, review, fonts);

      // SECTION 3: Canonical Rule Engine
      addCanonicalRules(document, review, fonts);

      // SECTION 4: Video Plan IR
      addVideoPlanIR(document, workflow, review, fonts);

      // SECTION 5: Creative Quality
      addCreativeQuality(document, review, fonts);

      // SECTION 6: LocalExecutionCritic
      addLocalExecutionCritic(document, review, fonts);

      // SECTION 7: Evidence & Source Traceability
      addEvidenceTraceability(document, workflow, review, fonts);

      // SECTION 8: F8 Render Authorization
      addF8Authorization(document, review, fonts);

      // SECTION 9: Findings Resolution
      addFindingsResolution(document, review, fonts);

      // SECTION 10: Next Steps
      addFullAnalysisNextSteps(document, workflow, review, fonts);

    } catch (IOException | RuntimeException e) {
      throw new QualityReportPdfException("Full analysis PDF could not be rendered", e);
    } finally {
      if (document.isOpen()) document.close();
    }
    return out.toByteArray();
  }

  private void addFullAnalysisHeader(Document document, Map<String, Object> workflow,
      Map<String, Object> review, Fonts fonts) throws DocumentException {
    document.add(new Paragraph("POMPOM HILLS CREATIVE INTELLIGENCE", fonts.eyebrow));
    document.add(new Paragraph("Quality Analysis Report", fonts.title));
    document.add(new Paragraph(
        "Evidence-backed analysis of the saved production prompt", fonts.muted));

    String contentId = humanize(firstValue(review, "contentId"), "UNKNOWN");
    String promptVersionId = humanize(firstValue(review, "promptVersionId"),
        "UNKNOWN");
    String profile = humanize(firstValue(review, "boundRequest.contentProfile", "routing.contentProfile"),
        "UNKNOWN");
    String generator = humanize(firstValue(review, "boundRequest.generator", "generation.selectedGenerator"),
        "UNKNOWN");
    String duration = humanize(firstValue(review, "boundRequest.desiredDuration", "generation.desiredDuration"), "UNKNOWN");
    String aspectRatio = humanize(firstValue(review, "boundRequest.settings.aspectRatio", "generation.settings.aspectRatio"),
        "UNKNOWN");
    String ruleset = humanize(firstValue(review, "canonicalRuleEvaluation.rulesetVersion"), "UNKNOWN");
    String score = "UNKNOWN";
    String grade = "UNKNOWN";
    if (review != null && review.get("canonicalRuleEvaluation") instanceof Map<?, ?> canonical) {
      score = humanize(canonical.get("score"), "UNKNOWN");
      grade = humanize(canonical.get("grade"), "UNKNOWN");
    }

    PdfPTable table = new PdfPTable(new float[] {50, 50});
    table.setWidthPercentage(100);
    table.setSpacingBefore(10);
    table.setSpacingAfter(12);

    PdfPCell left = plainCell(new Color(0xEAF4EE), 10);
    left.addElement(new Paragraph("ANALYSIS IDENTITY", fonts.eyebrow));
    left.addElement(new Paragraph("Saved run: " + review.get("recordId"), fonts.small));
    left.addElement(new Paragraph("Analysed: " + workflowEvidenceText(review.get("createdAt")), fonts.small));
    left.addElement(new Paragraph("Settings: " + workflowEvidenceText(firstValue(review, "boundRequest.settings")), fonts.small));
    left.addElement(new Paragraph("Content: " + contentId, fonts.body));
    left.addElement(new Paragraph("Prompt version: " + promptVersionId, fonts.body));
    left.addElement(new Paragraph("Profile: " + profile, fonts.body));
    left.addElement(new Paragraph("Generator: " + generator, fonts.body));
    left.addElement(new Paragraph("Duration: " + duration + " · Aspect ratio: " + aspectRatio, fonts.body));
    left.addElement(new Paragraph("Ruleset: " + ruleset, fonts.body));
    left.addElement(new Paragraph("Source: " + workflowEvidenceText(firstValue(review, "source.artifact")), fonts.small));
    left.addElement(new Paragraph("Prompt SHA256: " + workflowEvidenceText(firstValue(review, "source.sha256")), fonts.small));
    table.addCell(left);

    PdfPCell right = plainCell(new Color(0xEAF1FB), 10);
    right.addElement(new Paragraph("QUALITY SCORE", fonts.eyebrow));
    right.addElement(new Paragraph(score + " / 100", fonts.heading));
    right.addElement(new Paragraph("Grade: " + grade, fonts.bold));
    right.addElement(new Paragraph("Export: " + ZonedDateTime.now(ZoneId.of("UTC")).format(TIMESTAMP), fonts.muted));
    table.addCell(right);

    document.add(table);
  }

  private void addFullAnalysisSummary(Document document, Map<String, Object> workflow,
      Map<String, Object> review, Fonts fonts) throws DocumentException {
    section(document, "Executive Summary", fonts);

    String decision = "COMPLETED";
    String recommendation = "Review required findings";
    String authStatus = "BLOCKED";
    if (review != null) {
      decision = humanize(review.get("reviewStatus"), humanize(review.get("status"), "COMPLETED"));
      if (review.get("planQuality") instanceof Map<?, ?> pq) {
        recommendation = humanize(pq.get("recommendation"), recommendation);
      }
      if (review.get("family8") instanceof Map<?, ?> f8
          && f8.get("renderAuthorization") instanceof Map<?, ?> auth) {
        authStatus = humanize(auth.get("status"), "BLOCKED");
      }
    }

    PdfPTable cards = new PdfPTable(new float[] {25, 25, 25, 25});
    cards.setWidthPercentage(100);
    cards.setSpacingBefore(8);
    cards.addCell(metricCell("ANALYSIS", decision, BLUE, fonts));
    cards.addCell(metricCell("CREATIVE", humanize(firstValue(review, "planQuality.status"), "UNKNOWN"), ORANGE, fonts));
    cards.addCell(metricCell("RENDER AUTH", authStatus, RED, fonts));
    cards.addCell(metricCell("RECOMMENDATION", recommendation, GREEN, fonts));
    document.add(cards);

    document.add(new Paragraph(
        "This report uses the saved Step 5 analysis. It does not call any provider or rerun evaluation.",
        fonts.muted));
  }

  private void addCanonicalRules(Document document, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "Canonical Rule Engine Report", fonts);
    if (review == null || !(review.get("canonicalRuleEvaluation") instanceof Map<?, ?> canonical)) {
      document.add(new Paragraph("Canonical rule evaluation not available for this analysis.", fonts.muted));
      return;
    }

    String ruleset = humanize(canonical.get("rulesetVersion"), "UNKNOWN");
    String score = humanize(canonical.get("score"), "UNKNOWN");
    String grade = humanize(canonical.get("grade"), "UNKNOWN");
    String status = humanize(canonical.get("status"), "UNKNOWN");
    int evaluated = intOf(canonical.get("rulesEvaluated"));

    document.add(new Paragraph("Ruleset: " + ruleset + " · Score: " + score + "/100 · Grade: " + grade
        + " · Status: " + status + " · Rules evaluated: " + evaluated, fonts.body));

    // Count outcomes
    int pass = 0, fail = 0, unknown = 0, na = 0;
    if (canonical.get("passedRules") instanceof List<?> passed) pass = passed.size();
    if (canonical.get("failedRules") instanceof List<?> failed) fail = failed.size();
    if (canonical.get("unknownRules") instanceof List<?> unknowns) unknown = unknowns.size();
    if (canonical.get("notApplicableRules") instanceof List<?> nas) na = nas.size();

    PdfPTable summary = new PdfPTable(new float[] {20, 20, 20, 20, 20});
    summary.setWidthPercentage(100);
    summary.setSpacingBefore(8);
    summary.addCell(metricCell("PASS", String.valueOf(pass), GREEN, fonts));
    summary.addCell(metricCell("FAIL", String.valueOf(fail), RED, fonts));
    summary.addCell(metricCell("UNKNOWN", String.valueOf(unknown), MUTED, fonts));
    summary.addCell(metricCell("NOT APPLICABLE", String.valueOf(na), BORDER, fonts));
    summary.addCell(metricCell("EVALUATED", String.valueOf(evaluated), BLUE, fonts));
    document.add(summary);

    document.add(new Paragraph("Individual Rule Outcomes", fonts.heading));
    PdfPTable table = new PdfPTable(new float[] {18, 82});
    table.setWidthPercentage(100); table.setHeaderRows(1);
    table.setSpacingBefore(10); table.setSpacingAfter(12);
    header(table, fonts, "Outcome", "Rule / recorded evidence");
    for (List<?> list : List.of(
        canonical.get("passedRules") instanceof List<?> l ? l : List.of(),
        canonical.get("failedRules") instanceof List<?> l ? l : List.of(),
        canonical.get("unknownRules") instanceof List<?> l ? l : List.of(),
        canonical.get("notApplicableRules") instanceof List<?> l ? l : List.of())) {
      for (Object item : list) {
        if (!(item instanceof Map<?, ?> rule)) continue;
        String outcome = humanize(rule.get("outcome"), humanize(rule.get("status"), "UNKNOWN"));
        table.addCell(cell(outcome, fonts.colored(fonts.body, outcome.contains("NOT APPLICABLE") ? MUTED : outcome.equals("UNKNOWN") ? ORANGE : statusColor(outcome)), null));
        PdfPCell details = plainCell(Color.WHITE, 9);
        details.addElement(new Paragraph(workflowEvidenceText(rule.get("ruleId")), fonts.bold));
        details.addElement(new Paragraph("Family: " + humanize(rule.get("family"), "UNKNOWN") + " | Configured severity: " + humanize(rule.get("severity"), "UNKNOWN"), fonts.small));
        details.addElement(new Paragraph(humanize(rule.get("message"), "UNKNOWN"), fonts.body));
        table.addCell(details);
      }
    }
    document.add(table);
  }

  private void addVideoPlanIR(Document document, Map<String, Object> extraction, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "Video Plan IR", fonts);
    if (!(firstValue(review, "canonicalRuleEvaluation.videoPlanIR") instanceof Map<?,?> historical)) {
      document.add(new Paragraph("Historical Video Plan IR not available (UNKNOWN).", fonts.muted)); return;
    }
    boolean current = extraction != null && "READ_ONLY_SOURCE_EXTRACTION".equals(extraction.get("kind"))
        && firstValue(extraction,"source.sha256") != null
        && firstValue(extraction,"source.sha256").equals(firstValue(review,"source.sha256"))
        && extraction.get("videoPlanIR") instanceof Map<?,?>;
    Map<?,?> ir = current ? (Map<?,?>)extraction.get("videoPlanIR") : historical;
    if(current) {
      document.add(new Paragraph("Read-only source extraction - not revalidation", fonts.bold));
      document.add(new Paragraph("Extraction identity: " + workflowEvidenceText(extraction.get("resultId")), fonts.small));
      document.add(new Paragraph("Parent saved run: " + review.get("recordId"), fonts.small));
      document.add(new Paragraph("Current parser fields are supplemental textual evidence. Historical IR, canonical score/grade and F8 remain unchanged. Independent semantic validation NOT_PERFORMED; authorization NOT_EVALUATED.", fonts.body));
    } else document.add(new Paragraph("Current source extraction unavailable (UNKNOWN); historical IR is displayed without enrichment.", fonts.muted));
    document.add(new Paragraph("Character: " + humanize(ir.get("mainCharacter"), "UNKNOWN") + " | " + humanize(firstValue(extraction,"videoPlanIR.entityEvidence.mainCharacter.state"),"UNKNOWN"), fonts.body));
    document.add(new Paragraph("Principal object: " + humanize(ir.get("principalObject"), "UNKNOWN") + " | " + humanize(firstValue(extraction,"videoPlanIR.entityEvidence.principalObject.state"),"UNKNOWN"), fonts.body));
    if(current) provenanceTable(document,"Source entity provenance",firstValue(extraction,"videoPlanIR.entityEvidence"),fonts);
    document.add(new Paragraph("Historical canonical character/object fields: " + humanize(historical.get("mainCharacter"),"UNKNOWN") + " / " + humanize(historical.get("principalObject"),"UNKNOWN"), fonts.small));
    document.add(new Paragraph("Recorded physical mechanic: " + workflowEvidenceText(historical.get("coreMechanic")), fonts.body));
    document.add(new Paragraph("Recorded goal evidence: " + workflowEvidenceText(historical.get("goalEvidence")), fonts.body));
    document.add(new Paragraph("Recurrence: " + humanize(historical.get("recurrence"), "UNKNOWN"), fonts.body));
    if (ir.get("beats") instanceof List<?> beats && !beats.isEmpty()) {
      document.add(new Paragraph("Timed Beats (" + beats.size() + ")", fonts.heading));
      PdfPTable table = new PdfPTable(new float[] {13, 24, 63});
      table.setWidthPercentage(100); table.setHeaderRows(1);table.setSpacingBefore(10);table.setSpacingAfter(12);
      header(table, fonts, "Time", "Actor / object", "Action / consequence / source evidence");
      for(Object value: beats) {
        if(!(value instanceof Map<?,?> beat))continue;
        table.addCell(cell(humanize(beat.get("startTime"),"UNKNOWN") + "-" + humanize(beat.get("endTime"),"UNKNOWN") + " s",fonts.body,null));
        PdfPCell entities=plainCell(Color.WHITE,8);
        entities.addElement(new Paragraph("Actor: " + humanize(beat.get("actor"),"UNKNOWN"),fonts.bold));
        entities.addElement(new Paragraph("Object: " + humanize(beat.get("primaryObject"),"UNKNOWN"),fonts.body));
        Object fields=beat.get("fieldEvidence");
        Map<?,?> fieldMap=fields instanceof Map<?,?> map?map:Map.of();
        for(String field:List.of("actor","primaryObject")) {
          Map<?,?> ev=fieldMap.get(field) instanceof Map<?,?> map?map:Map.of();
          entities.addElement(new Paragraph(field + ": " + workflowEvidenceText(ev.get("state")),fonts.small));
          if(ev.get("sourceQuote")!=null)entities.addElement(new Paragraph("Quote: " + ev.get("sourceQuote") + " | span " + workflowEvidenceText(ev.get("sourceSpan")),fonts.small));
        }
        table.addCell(entities);
        PdfPCell action=plainCell(Color.WHITE,9);
        String displayAction=current?workflowEvidenceText(beat.get("sourceAction")):cleanBeatAction(beat);
        action.addElement(new Paragraph("Action",fonts.bold));action.addElement(new Paragraph(displayAction,fonts.body));
        action.addElement(new Paragraph("Consequence",fonts.bold));action.addElement(new Paragraph(cleanSourceSectionText(workflowEvidenceText(beat.get("consequence"))),fonts.body));
        action.addElement(new Paragraph("Source span: " + workflowEvidenceText(beat.get("sourceSpan")) + " | " + workflowEvidenceText(beat.get("sourceSpanStatus")),fonts.small));
        if(fieldMap.get("primaryObject") instanceof Map<?,?> ev && "INFERRED".equals(ev.get("state")))action.addElement(new Paragraph(workflowEvidenceText(ev.get("reason")),fonts.small));
        table.addCell(action);
      }
      document.add(table);
    }
  }

  private String cleanBeatAction(Map<?,?> beat) {
    String quote=cleanSourceSectionText(workflowEvidenceText(beat.get("sourceQuote") == null ? beat.get("action") : beat.get("sourceQuote")));
    return quote.replaceFirst("^\\d+(?:\\.\\d+)?\\s*[-–—]\\s*\\d+(?:\\.\\d+)?\\s*(?:s|sec|seconds)?\\s*:?\\s*", "").split("\\[|->|\\n",2)[0].trim();
  }

  private void addCreativeQuality(Document document, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "Creative Quality Assessment", fonts);
    if (review == null) {
      document.add(new Paragraph("No creative quality assessment available.", fonts.muted));
      return;
    }

    PdfPTable table = new PdfPTable(new float[] {26, 18, 56});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    table.setSpacingBefore(10);table.setSpacingAfter(12);
    header(table, fonts, "Dimension", "Recorded status", "Explanation");

    // Opening
    String opening = "UNKNOWN";
    String openingNote = "No separate opening assessment; planned first beat extracted but no visual verification.";
    if (review.get("planQuality") instanceof Map<?, ?> pq) {
      if (pq.get("opening") instanceof Map<?, ?> o) {
        opening = humanize(o.get("assessment"), humanize(o.get("status"), "UNKNOWN"));
        openingNote = cleanSourceSectionText(humanize(o.get("plannedFirstBeat"), humanize(o.get("reason"), openingNote)));
      }
    }
    table.addCell(cell("Opening / first-frame hook", fonts.bold, null));
    table.addCell(cell(opening, fonts.colored(fonts.small, statusColor(opening)), null));
    table.addCell(cell(openingNote, fonts.small, null));

    // Progression
    String progression = "UNKNOWN";
    String progressionNote = "Insufficient evidence from text alone; planned beats exist but meaningful progression quality is unverified.";
    if (review.get("planQuality") instanceof Map<?, ?> pq) {
      if (pq.get("progression") instanceof Map<?, ?> p) {
        progression = humanize(p.get("assessment"), humanize(p.get("status"), "UNKNOWN"));
        progressionNote = humanize(p.get("reason"), progressionNote);
      }
    }
    table.addCell(cell("Beat progression", fonts.bold, null));
    table.addCell(cell(progression, fonts.colored(fonts.small, statusColor(progression)), null));
    table.addCell(cell(progressionNote, fonts.small, null));

    // Ending
    String ending = "UNKNOWN";
    String endingNote = "Planned last beat extracted; payoff quality unassessable without visual evidence.";
    if (review.get("planQuality") instanceof Map<?, ?> pq) {
      if (pq.get("ending") instanceof Map<?, ?> e) {
        ending = humanize(e.get("assessment"), humanize(e.get("status"), "UNKNOWN"));
        endingNote = cleanSourceSectionText(humanize(e.get("plannedLastBeat"), humanize(e.get("reason"), endingNote)));
      }
    }
    table.addCell(cell("Ending / payoff", fonts.bold, null));
    table.addCell(cell(ending, fonts.colored(fonts.small, statusColor(ending)), null));
    table.addCell(cell(endingNote, fonts.small, null));

    // Physical rule consistency
    table.addCell(cell("Physical rule consistency", fonts.bold, null));
    table.addCell(cell("UNKNOWN", fonts.colored(fonts.small, statusColor("UNKNOWN")), null));
    table.addCell(cell("Independent semantic and rendered physical consistency are UNKNOWN; inspect the saved IR above.", fonts.small, null));

    // Action variety
    table.addCell(cell("Action variety", fonts.bold, null));
    table.addCell(cell("UNKNOWN", fonts.colored(fonts.small, statusColor("UNKNOWN")), null));
    table.addCell(cell("Distinct action variety is not independently verified by this export.", fonts.small, null));

    document.add(table);
  }

  private void addLocalExecutionCritic(Document document, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "Local Execution Critic", fonts);
    if (review == null) {
      document.add(new Paragraph("No LocalExecutionCritic data available.", fonts.muted));
      return;
    }

    String planQuality = "UNKNOWN";
    String execRisk = "UNKNOWN";
    String producibility = "UNKNOWN";
    if (review.get("planQuality") instanceof Map<?, ?> pq) {
      planQuality = humanize(pq.get("status"), "UNKNOWN");
    }
    if (review.get("executionRisk") instanceof Map<?, ?> er) {
      execRisk = humanize(er.get("status"), "UNKNOWN");
    }
    if (review.get("generalProducibility") instanceof Map<?, ?> gp) {
      producibility = humanize(gp.get("status"), humanize(gp.get("overallStatus"), "UNKNOWN"));
    }

    PdfPTable table = new PdfPTable(new float[] {26, 18, 56});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    table.setSpacingBefore(10);table.setSpacingAfter(12);
    header(table, fonts, "Dimension", "Recorded status", "Explanation");

    table.addCell(cell("Plan quality", fonts.bold, null));
    table.addCell(cell(planQuality, fonts.colored(fonts.small, statusColor(planQuality)), null));
    table.addCell(cell("Text-based plan assessment; no image evidence.", fonts.small, null));

    table.addCell(cell("Local execution check", fonts.bold, null));
    table.addCell(cell(execRisk, fonts.colored(fonts.small, statusColor(execRisk)), null));
    table.addCell(cell("PASS means no local text findings were recorded; actual generator success is UNKNOWN.", fonts.small, null));

    table.addCell(cell("Production complexity", fonts.bold, null));
    table.addCell(cell(producibility, fonts.colored(fonts.small, statusColor(producibility)), null));
    table.addCell(cell("Text-based producibility assessment; actual render success remains UNKNOWN.", fonts.small, null));

    document.add(table);

    document.add(new Paragraph("Generator capability: " + workflowEvidenceText(firstValue(review, "generation.capabilityStatus"))
        + " - schema snapshot " + workflowEvidenceText(firstValue(review, "generation.profileVersion")), fonts.body));
    provenanceTable(document,"Capability provenance",firstValue(review,"generation.capabilityProvenance"),fonts);
    document.add(new Paragraph("Execution findings: " + workflowEvidenceText(firstValue(review, "executionReview.findings")), fonts.small));
    document.add(new Paragraph("Execution limitations: " + workflowEvidenceText(firstValue(review, "executionReview.limitations")), fonts.small));
    document.add(new Paragraph("Material producibility risks: " + workflowEvidenceText(firstValue(review, "generalProducibility.materialRisks")), fonts.body));
    PdfPTable risksTable = new PdfPTable(new float[] {24, 12, 64});
    risksTable.setWidthPercentage(100); risksTable.setHeaderRows(1);risksTable.setSpacingBefore(10);risksTable.setSpacingAfter(12);
    header(risksTable, fonts, "Material dimension", "Level", "Recorded reason / references");
    Object dimensions=firstValue(review, "generalProducibility.dimensions");
    for (Object key : listValue(firstValue(review, "generalProducibility.materialRisks"))) {
      if (!(dimensions instanceof Map<?,?> dims) || !(dims.get(key) instanceof Map<?,?> dimension)) continue;
      risksTable.addCell(cell(humanize(key, "UNKNOWN"), fonts.small, null));
      risksTable.addCell(cell(workflowEvidenceText(dimension.get("level")), fonts.small, null));
      risksTable.addCell(cell(workflowEvidenceText(dimension.get("reason")) + " - references: " + workflowEvidenceText(dimension.get("evidenceReferences")), fonts.body, null));
    }
    document.add(risksTable);
    document.add(new Paragraph("Unknown dimensions: " + workflowEvidenceText(firstValue(review, "generalProducibility.unknownDimensions")), fonts.small));
    document.add(new Paragraph("Duration load: " + workflowEvidenceText(firstValue(review, "generalProducibility.durationLoad")), fonts.small));
    // Risks
    if (review.get("generalProducibility") instanceof Map<?, ?> gp
        && gp.get("risks") instanceof List<?> risks && !risks.isEmpty()) {
      document.add(new Paragraph("Production Risks", fonts.heading));
      for (Object risk : risks) {
        if (risk instanceof Map<?, ?> r) {
          String dim = humanize(r.get("dimension"), humanize(r.get("risk"), "UNKNOWN"));
          String level = humanize(r.get("level"), humanize(r.get("severity"), "UNKNOWN"));
          String msg = humanize(r.get("message"), humanize(r.get("explanation"), ""));
          String riskText = dim + ": " + level;
          if (!msg.isBlank()) riskText += " — " + msg;
          document.add(new Paragraph(riskText, fonts.small));
        }
      }
    }
  }

  private void addEvidenceTraceability(Document document, Map<String, Object> workflow,
      Map<String, Object> review, Fonts fonts) throws DocumentException {
    section(document, "Evidence & Source Traceability", fonts);
    document.add(new Paragraph("Source identity: " + workflowEvidenceText(firstValue(review, "source")), fonts.body));
    provenanceTable(document,"Production evidence provenance",firstValue(review,"generalProducibility.provenance.sourceEvidence"),fonts);
    document.add(new Paragraph("Independent semantic fidelity: UNKNOWN. Source ancestry and quote correspondence do not establish semantic approval. Rendered fidelity requires Video QA.", fonts.body));
    document.add(new Paragraph("Legacy provider traceability is separate. No approved-story linkage or sentence mapping is inferred by this export when absent from the saved run.", fonts.muted));
    document.add(new Paragraph("Remaining uncertainty: " + workflowEvidenceText(firstValue(review, "productionEvidence.remainingUncertainty")), fonts.body));
    for (Object claim : listValue(firstValue(review, "productionEvidence.claims"))) {
      if (claim instanceof Map<?,?> row && ("CONTRADICTORY".equals(row.get("state")) || "INVALID".equals(row.get("state"))))
        document.add(new Paragraph("Recorded validation diagnostic: " + workflowEvidenceText(row), fonts.small));
    }
    document.add(new Paragraph(technicalDiagnostic(review), fonts.body));
    document.add(new Paragraph("Creative evidence limitations: " + workflowEvidenceText(firstValue(review, "planQuality.limitations")), fonts.small));
  }

  private void addF8Authorization(Document document, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "F8 Render Authorization", fonts);
    if (review == null || !(review.get("family8") instanceof Map<?, ?> f8)
        || !(f8.get("renderAuthorization") instanceof Map<?, ?> auth)) {
      document.add(new Paragraph("Render authorization data not available.", fonts.muted));
      return;
    }

    String status = humanize(auth.get("status"), "BLOCKED");
    document.add(new Paragraph("Status: " + status,
        fonts.colored(fonts.heading, statusColor(status))));

    if (auth.get("reasons") instanceof List<?> reasons && !reasons.isEmpty()) {
      document.add(new Paragraph("Authorization Reasons", fonts.heading));
      PdfPTable table = new PdfPTable(new float[] {24, 20, 56});
      table.setWidthPercentage(100);
      table.setHeaderRows(1);
      table.setSpacingBefore(10);table.setSpacingAfter(12);
      header(table, fonts, "Code", "Source", "Historical message / evidence (not independently verified)");

      for (Object reason : reasons) {
        if (reason instanceof Map<?, ?> r) {
          String code = workflowEvidenceText(r.get("code"));
          String rStatus = workflowEvidenceText(r.get("source"));
          String msg = humanize(r.get("message"), "") + " - references: " + workflowEvidenceText(r.get("references"));
          table.addCell(cell(code, fonts.small, null));
          table.addCell(cell(rStatus, fonts.small, null));
          table.addCell(cell(msg, fonts.small, null));
        }
      }
      document.add(table);
    }

    document.add(new Paragraph(technicalDiagnostic(review), fonts.body));
    document.add(new Paragraph(
        "Render authorization is not granted by this report. Explicit user approval remains mandatory.",
        fonts.muted));
  }

  private void addFindingsResolution(Document document, Map<String, Object> review, Fonts fonts)
      throws DocumentException {
    section(document, "Findings Resolution", fonts);
    document.add(new Paragraph("Plan findings: " + workflowEvidenceText(firstValue(review, "planQuality.findings")), fonts.body));
    document.add(new Paragraph("Local execution findings: " + workflowEvidenceText(firstValue(review, "executionReview.findings")), fonts.body));
    for (Object value : listValue(firstValue(review, "family8.renderAuthorization.reasons"))) {
      if (!(value instanceof Map<?,?> reason)) continue;
      String source=workflowEvidenceText(reason.get("source"));
      String action=source.equals("REFERENCE_ASSOCIATION") ? "Select and bind a verified canonical character reference in Step 7."
          : source.equals("EXECUTION_INPUTS") ? "Prepare and accept a first frame in Step 7; generation is separately opt-in."
          : String.valueOf(reason.get("code")).contains("TECHNICAL") ? "Inspect the saved validation diagnostic and input contract. No story change is justified by this failure alone."
          : "Inspect the recorded evidence before revalidation.";
      document.add(new Paragraph(workflowEvidenceText(reason.get("code")) + " / " + source + ": " + action, fonts.body));
    }
  }

  private void addFullAnalysisNextSteps(Document document, Map<String, Object> workflow,
      Map<String, Object> review, Fonts fonts) throws DocumentException {
    section(document, "Conclusions & Next Action", fonts);
    document.add(new Paragraph("This export preserves run " + review.get("recordId") + ". It does not rerun analysis, change the canonical score, or authorize render.", fonts.body));
    document.add(new Paragraph("Canonical outcomes and source intervals above are the recorded evidence. Independent story fidelity and actual rendered quality remain UNKNOWN.", fonts.body));
    document.add(new Paragraph("Resolve the recorded technical diagnostic, supply missing references and execution inputs, then independently revalidate the exact saved request. Explicit authorization is still required for rendering.", fonts.body));
  }

  // Helper: get a value from a map, trying multiple keys
  private Object firstValue(Map<String, Object> map, String... keys) {
    if (map == null) return null;
    for (String key : keys) {
      if (key == null) continue;
      Object value=map;
      for (String part : key.split("\\.")) value=value instanceof Map<?,?> nested ? nested.get(part) : null;
      if (value != null) return value;
    }
    return null;
  }

  private List<?> listValue(Object value) { return value instanceof List<?> rows ? rows : List.of(); }

  private String workflowEvidenceText(Object value) {
    if(value == null) return "UNKNOWN";
    if(value instanceof Map<?,?> map) return map.entrySet().stream().map(e -> e.getKey() + ": " + workflowEvidenceText(e.getValue())).collect(java.util.stream.Collectors.joining("; "));
    if(value instanceof List<?> rows) return rows.isEmpty() ? "None recorded" : rows.stream().map(this::workflowEvidenceText).collect(java.util.stream.Collectors.joining("; "));
    return englishText(String.valueOf(value));
  }

  private String technicalDiagnostic(Map<String,Object> review) {
    if (!"BLOCKED_TECHNICAL_FAILURE".equals(firstValue(review, "family8.renderAuthorization.status"))) return "No technical authorization failure recorded.";
    String diagnostic=firstValue(review, "boundRequest.structuredPlan.events") != null && firstValue(review, "boundRequest.structuredPlan.beats") == null
        ? "Saved input-contract mismatch: deterministic events were supplied to a validator expecting source-bound beats. " : "";
    return diagnostic + "Recorded technical failure remains blocking. Runtime exception details and independently conflicting source spans were not saved; contradiction evidence is UNKNOWN.";
  }

  private void provenanceTable(Document document,String title,Object value,Fonts fonts) throws DocumentException {
    document.add(new Paragraph(title,fonts.bold));
    if(!(value instanceof Map<?,?> evidence)){document.add(new Paragraph("UNKNOWN",fonts.body));return;}
    PdfPTable table=new PdfPTable(new float[]{26,74});table.setWidthPercentage(100);table.setSpacingBefore(8);table.setSpacingAfter(12);
    for(var entry:evidence.entrySet()){table.addCell(cell(String.valueOf(entry.getKey()),fonts.small,null));table.addCell(cell(workflowEvidenceText(entry.getValue()),fonts.small,null));}
    document.add(table);
  }

  private int intOf(Object val) {
    if (val instanceof Number n) return n.intValue();
    if (val instanceof String s) {
      try { return Integer.parseInt(s.trim()); } catch (NumberFormatException e) { return 0; }
    }
    return 0;
  }

  private void addWorkflowHeader(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    document.add(new Paragraph("PRODUCTION REVIEW", fonts.eyebrow));
    document.add(new Paragraph("Creative Intelligence Report", fonts.title));
    document.add(new Paragraph("Evidence-led review of the saved production workflow", fonts.muted));
    PdfPTable banner = new PdfPTable(new float[] {68, 32});
    banner.setWidthPercentage(100);
    banner.setSpacingBefore(10);
    banner.setSpacingAfter(12);
    PdfPCell left = plainCell(new Color(0xEAF4EE), 10);
    left.addElement(new Paragraph("DECISION", fonts.eyebrow));
    left.addElement(new Paragraph(humanize(snapshot.get("decision"), "Review completed"), fonts.heading));
    left.addElement(new Paragraph("Policy: " + humanize(snapshot.get("decisionPolicyVersion"), "Historical policy"), fonts.muted));
    banner.addCell(left);
    PdfPCell right = plainCell(new Color(0xEAF1FB), 10);
    right.addElement(new Paragraph("RECORD", fonts.eyebrow));
    right.addElement(new Paragraph("Saved workflow", fonts.bold));
    right.addElement(new Paragraph("Binding " + shortValue(snapshot.get("bindingHash")), fonts.muted));
    banner.addCell(right);
    document.add(banner);
  }

  private void addWorkflowSummary(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    section(document, "Executive summary", fonts);
    String summary = firstText(snapshot, "summary", "reviewSummary", "operatorSummary");
    if (summary.isBlank()) summary = "The saved workflow was reviewed against the configured creative and production requirements.";
    document.add(new Paragraph(summary, fonts.body));
    PdfPTable cards = new PdfPTable(new float[] {25, 25, 25, 25});
    cards.setWidthPercentage(100);
    cards.setSpacingBefore(8);
    cards.addCell(metricCell("PROMPT PLAN", dimensionStatus(snapshot, "promptPlanQuality"), BLUE, fonts));
    cards.addCell(metricCell("GENERATOR RISK", dimensionStatus(snapshot, "generatorExecutionRisk"), ORANGE, fonts));
    cards.addCell(metricCell("RENDER QUALITY", dimensionStatus(snapshot, "actualRenderQuality"), GREEN, fonts));
    cards.addCell(metricCell("AUDIENCE", dimensionStatus(snapshot, "audienceDistributionOutcome"), AMBER, fonts));
    document.add(cards);
    addWorkflowStatusBlock(document, snapshot, fonts);
  }

  private void addWorkflowStatusBlock(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    PdfPTable table = new PdfPTable(new float[] {36, 64});
    table.setWidthPercentage(100);
    table.setSpacingBefore(10);
    table.setHeaderRows(1);
    header(table, fonts, "Decision signal", "Recorded interpretation");
    addEvidenceRow(table, fonts, "Analysis execution", snapshot.getOrDefault("analysisExecutionStatus", "COMPLETED"));
    addEvidenceRow(table, fonts, "Creative assessment", snapshot.getOrDefault("creativeAssessmentStatus", dimensionStatus(snapshot, "promptPlanQuality")));
    addEvidenceRow(table, fonts, "Evidence completeness", snapshot.getOrDefault("evidenceStatus", "INCOMPLETE"));
    addEvidenceRow(table, fonts, "Render authorization", snapshot.getOrDefault("authorizationStatus", "BLOCKED_UNTIL_EVIDENCE"));
    addEvidenceRow(table, fonts, "Recommendation", snapshot.getOrDefault("recommendation", "Review required findings"));
    document.add(table);
  }

  private void addWorkflowDimensions(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    section(document, "Review dimensions", fonts);
    Map<?, ?> dimensions = snapshot.get("reviewDimensions") instanceof Map<?, ?> m ? m : Map.of();
    PdfPTable table = new PdfPTable(new float[] {26, 16, 58});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    header(table, fonts, "Dimension", "Status", "What this means");
    List<String[]> rows = List.of(
        new String[] {"Prompt plan quality", "promptPlanQuality", "Whether the prompt preserves the approved creative intent and beat structure."},
        new String[] {"Generator execution risk", "generatorExecutionRisk", "Practical risks that could make the prompt difficult for a video generator to execute."},
        new String[] {"Actual render quality", "actualRenderQuality", "Observed output quality from available render evidence."},
        new String[] {"Audience distribution outcome", "audienceDistributionOutcome", "Expected clarity, retention and audience-facing outcome."});
    for (String[] row : rows) {
      Map<?, ?> value = dimensions.get(row[1]) instanceof Map<?, ?> m ? m : Map.of();
      String status = humanize(value.get("status"), value.isEmpty() ? "UNKNOWN" : "Recorded");
      table.addCell(cell(row[0], fonts.bold, null));
      table.addCell(cell(status, fonts.colored(fonts.small, statusColor(status)), null));
      String detail = firstText(value, "summary", "assessment", "reason", "message");
      if (detail.isBlank()) detail = row[2];
      table.addCell(cell(detail, fonts.small, null));
    }
    document.add(table);
  }

  private void addWorkflowEvidence(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    section(document, "Evidence and production settings", fonts);
    PdfPTable table = new PdfPTable(new float[] {30, 70});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    header(table, fonts, "Evidence item", "Recorded value");
    addEvidenceRow(table, fonts, "Authorization scope", snapshot.getOrDefault("authorizationScope", "PROMPT_WORKFLOW"));
    addEvidenceRow(table, fonts, "Family 8 status", snapshot.getOrDefault("family8", "UNKNOWN"));
    addEvidenceRow(table, fonts, "Audio review", snapshot.getOrDefault("audioReview", "UNKNOWN"));
    addEvidenceRow(table, fonts, "Binding reference", snapshot.getOrDefault("bindingHash", "UNKNOWN"));
    addEvidenceRow(table, fonts, "Evidence state", snapshot.getOrDefault("evidenceStatus", "Recorded in workflow"));
    document.add(table);
    if (snapshot.get("operatorReport") instanceof List<?> rows && !rows.isEmpty()) {
      document.add(new Paragraph("Reviewer notes", fonts.heading));
      String viewingMechanism = rows.stream()
          .filter(Map.class::isInstance)
          .map(Map.class::cast)
          .filter(row -> englishLabel(row.get("label")).equalsIgnoreCase("Viewing mechanism"))
          .map(row -> cleanSourceSectionText(englishText(row.get("text") == null ? "" : String.valueOf(row.get("text")))))
          .findFirst().orElse("");
      for (Object item : rows) if (item instanceof Map<?, ?> row) {
        String label = englishLabel(row.get("label"));
        String text = cleanSourceSectionText(englishText(row.get("text") == null ? "" : String.valueOf(row.get("text"))));
        if (label.equalsIgnoreCase("Opening") && !viewingMechanism.isBlank() && text.equals(viewingMechanism)) {
          text = "Same source observation as the viewing mechanism; no separate opening assessment was recorded.";
        }
        if (!text.isBlank()) document.add(labelled(label + ": ", text, fonts));
      }
    }
  }

  private void addWorkflowBeats(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    Object raw = snapshot.get("beats");
    if (!(raw instanceof List<?> beats) || beats.isEmpty()) return;
    section(document, "Timed beat plan", fonts);
    PdfPTable table = new PdfPTable(new float[] {14, 18, 18, 50});
    table.setWidthPercentage(100);
    table.setHeaderRows(1);
    header(table, fonts, "Beat", "Time", "Framing", "Action");
    int i = 1;
    for (Object item : beats) if (item instanceof Map<?, ?> beat) {
      table.addCell(cell(String.valueOf(i++), fonts.bold, null));
      table.addCell(cell(firstText(beat, "time", "timeRange", "duration"), fonts.small, null));
      table.addCell(cell(firstText(beat, "framing", "shot", "camera"), fonts.small, null));
      table.addCell(cell(cleanSourceSectionText(englishText(firstText(beat, "action", "description", "text"))), fonts.small, null));
    }
    document.add(table);
  }

  private void addWorkflowNextSteps(Document document, Map<String, Object> snapshot, Fonts fonts)
      throws DocumentException {
    section(document, "Readiness and next actions", fonts);
    String authorization = humanize(snapshot.get("authorizationStatus"), "Review evidence before rendering");
    PdfPCell box = plainCell(new Color(0xFFF5DE), 10);
    box.addElement(new Paragraph("CURRENT READINESS", fonts.eyebrow));
    box.addElement(new Paragraph(authorization, fonts.heading));
    box.addElement(new Paragraph("This report records analysis evidence. Rendering and publishing still require their own explicit authorization.", fonts.body));
    PdfPTable wrap = new PdfPTable(1);
    wrap.setWidthPercentage(100);
    wrap.addCell(box);
    document.add(wrap);
    document.add(new Paragraph("Recommended next actions", fonts.heading));
    for (String action : List.of("Resolve UNKNOWN evidence items where source material is available.", "Review the timed beat plan and generator risks.", "Authorize rendering only after the approved prompt and evidence are final.")) {
      document.add(new Paragraph("• " + action, fonts.body));
    }
  }

  private void addEvidenceRow(PdfPTable table, Fonts fonts, String label, Object value) {
    table.addCell(cell(label, fonts.bold, null));
    String rendered = "Family 8 status".equals(label) ? family8Summary(value) : englishText(value == null ? "UNKNOWN" : String.valueOf(value));
    table.addCell(cell(rendered, fonts.small, null));
  }

  private String family8Summary(Object value) {
    if (!(value instanceof Map<?, ?> family8)) return englishText(value == null ? "UNKNOWN" : String.valueOf(value));
    Map<?, ?> creative = family8.get("creativeQuality") instanceof Map<?, ?> m ? m : Map.of();
    Map<?, ?> evidence = family8.get("evidenceCompleteness") instanceof Map<?, ?> m ? m : Map.of();
    Map<?, ?> authorization = family8.get("renderAuthorization") instanceof Map<?, ?> m ? m : Map.of();
    StringBuilder result = new StringBuilder();
    appendSummary(result, "Creative quality", creative.get("creativeGrade"), creative.get("creativeScore"));
    appendSummary(result, "Evidence completeness", evidence.get("status"), evidence.get("evaluationCoverage"));
    appendSummary(result, "Render authorization", authorization.get("status"), null);
    return result.isEmpty() ? "Recorded" : result.toString();
  }

  private void appendSummary(StringBuilder result, String label, Object status, Object score) {
    if (status == null && score == null) return;
    if (result.length() > 0) result.append("  ·  ");
    result.append(label).append(": ").append(humanize(status, "UNKNOWN"));
    if (score != null && !String.valueOf(score).equals("null")) result.append(" (" ).append(humanize(score, "UNKNOWN")).append(")");
  }

  private PdfPCell metricCell(String label, String value, Color color, Fonts fonts) {
    PdfPCell cell = plainCell(new Color(0xF7, 0xF9, 0xFB), 8);
    cell.setBorderColor(color);
    cell.setBorderWidth(1.2f);
    cell.addElement(new Paragraph(label, fonts.eyebrow));
    cell.addElement(new Paragraph(value, fonts.colored(fonts.bold, color)));
    return cell;
  }

  private String dimensionStatus(Map<String, Object> snapshot, String key) {
    Map<?, ?> dimensions = snapshot.get("reviewDimensions") instanceof Map<?, ?> m ? m : Map.of();
    Map<?, ?> value = dimensions.get(key) instanceof Map<?, ?> m ? m : Map.of();
    if (value.get("status") != null) return humanize(value.get("status"), "UNKNOWN");
    List<String> signals = new ArrayList<>();
    for (String field : List.of("planFidelity", "viewerFacingUsability", "editorialRecommendation", "evaluationCoverage")) {
      if (value.get(field) != null) signals.add(humanize(value.get(field), "UNKNOWN"));
    }
    return signals.isEmpty() ? "UNKNOWN" : String.join(" · ", signals);
  }

  private String firstText(Map<?, ?> map, String... keys) {
    for (String key : keys) {
      Object value = map.get(key);
      if (value != null && !String.valueOf(value).isBlank() && !"null".equalsIgnoreCase(String.valueOf(value))) return englishText(String.valueOf(value));
    }
    return "";
  }

  private String humanize(Object value, String fallback) {
    if (value == null || String.valueOf(value).isBlank() || "null".equalsIgnoreCase(String.valueOf(value))) return fallback;
    return englishText(String.valueOf(value)).replace('_', ' ');
  }

  private String shortValue(Object value) {
    String text = value == null ? "UNKNOWN" : String.valueOf(value);
    return text.length() > 18 ? text.substring(0, 18) + "…" : text;
  }

  private String englishLabel(Object value) {
    String text = value == null ? "Review note" : String.valueOf(value).trim().replaceFirst("\\s*:$", "");
    return switch (text.toUpperCase(Locale.ROOT)) {
      case "KARAR" -> "Decision";
      case "İZLEME MEKANİZMASI", "IZLEME MEKANIZMASI" -> "Viewing mechanism";
      case "AÇILIŞ", "ACILIS" -> "Opening";
      case "İLERLEME", "ILERLEME" -> "Progression";
      case "FİNAL", "FINAL" -> "Ending";
      case "TEMEL OLAY/KİMLİK/ANLAŞILABİLİRLİK", "TEMEL OLAY/KIMLIK/ANLASILABILIRLIK" -> "Core event / identity / clarity";
      case "TEKNİK KUSURLAR", "TEKNIK KUSURLAR" -> "Technical defects";
      case "KUSURUN ETKİSİ", "KUSURUN ETKISI" -> "Defect impact";
      case "EN KÜÇÜK MÜDAHALE", "EN KUCUK MUDAHALE" -> "Smallest intervention";
      case "PERFORMANS" -> "Performance";
      default -> englishText(text);
    };
  }

  private String cleanSourceSectionText(String value) {
    if (value == null) return "";
    String cleaned = value.replaceFirst("(?is)\\s*(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\\s*:?[\\s\\S]*$", "");
    return cleaned.replaceFirst("(?i)Planlanan final\\s*:", "Planned ending:")
        .replaceAll(":\\s*:", ":")
        .replaceFirst("^\\s*:\\s*", "")
        .trim();
  }

  private String englishText(String value) {
    if (value == null) return "";
    return value.replace(": :", ":")
        .replace(" : ", ": ")
        .replace("Dört ayrı değerlendirme boyutu", "Four review dimensions")
        .replace("Etki temelli prompt / video incelemesi", "Impact-based prompt and video review")
        .replace("Yayın izni değildir", "Does not authorize publishing")
        .replace("Yetkili karakter/nesne referansı eksik veya doğrulanmadı.", "Authorized character or object reference is missing or unverified.")
        .replace("Sağlayıcının zorunlu yürütme girdileri eksik: startFrame", "Required generator execution input is missing: startFrame")
        .replace("Çelişkili kaynak evidenceı.", "Conflicting source evidence.")
        .replace("Son video kabulü için mevcut doğrulanmış görsel kapılar ve bağımsız revalidation gereklidir.", "Verified visual gates and independent revalidation are required before final video acceptance.")
        .replace("Küçük prompt düzeltmesi önerilir", "A small prompt correction is recommended")
        .replace("Kanıt yetersiz", "Insufficient evidence")
        .replace("Karar için kanıt yetersiz", "Insufficient evidence for a decision")
        .replace("izleme gerekçesini değerlendirmek için kaynak evidence yetersiz", "Insufficient source evidence to evaluate viewing rationale")
        .replace("İzleme gerekçesini değerlendirmek için kaynak evidence yetersiz", "Insufficient source evidence to evaluate viewing rationale")
        .replace("İzleme gerekçesini değerlendirmek için kaynak evidenceı yetersiz", "Insufficient source evidence to evaluate viewing rationale")
        .replace("izleme gerekçesini değerlendirmek için kaynak evidenceı yetersiz", "Insufficient source evidence to evaluate viewing rationale")
        .replace("İzleme gerekçesini değerlendirmek için", "Viewing rationale:")
        .replace("izleme gerekçesini değerlendirmek için", "Viewing rationale:")
        .replace("kaynak evidenceı yetersiz", "insufficient source evidence")
        .replace("kaynak evidence yetersiz", "insufficient source evidence")
        .replaceAll("(?i)kaynak\\s+evidence.\\s+yetersiz", "insufficient source evidence")
        .replaceAll("(?i)kaynak.*yetersiz", "insufficient source evidence")
        .replace("Planlanan final", "Planned ending")
        .replace("Gerçek video henüz incelenmedi", "The final video has not been reviewed yet")
        .replace("Doğrulanmış kusur kanıtı yok", "No verified defect evidence")
        .replace("Doğrulanmış kusur evidenceı yok", "No verified defect evidence")
        .replace("Yalnız teknik temizlik yaratıcı değer kanıtı değildir", "Technical cleanliness alone is not creative value evidence")
        .replace("Yalnız teknik temizlik yaratıcı değer evidenceı değildir", "Technical cleanliness alone is not creative value evidence")
        .replace("Kör inceleme tamamlanana kadar sonuç verisi ayrıdır; izlenme garantisi yok", "Performance data remains separate until blind review is complete; no viewing guarantee")
        .replace("kanıt", "evidence")
        .replace("bilinmiyor", "UNKNOWN")
        .replace("tarihsel kayıtta bu boyut yok", "No historical evidence was recorded for this dimension")
        .replace("Yerel sapma; temel olay okunabilir.", "Local deviation; the core event remains readable.");
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
    Paragraph status =
        new Paragraph(clean(orDash(report.status())), fonts.colored(fonts.bold, statusColor));
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

  private void addGeneralProducibility(Document document, Object projection, Fonts fonts)
      throws DocumentException {
    String status =
        projection instanceof Map<?, ?> value ? orDash(str(value.get("status"))) : "UNKNOWN";
    Paragraph introduction = new Paragraph("General Producibility\n", fonts.heading);
    introduction.add(new Chunk("General Producibility: " + status, fonts.bold));
    introduction.setSpacingBefore(14);
    introduction.setSpacingAfter(5);
    introduction.setKeepTogether(true);
    document.add(introduction);
    if (!(projection instanceof Map<?, ?> evidence)) {
      document.add(
          new Paragraph(
              "No production feasibility evidence in this historical report.", fonts.muted));
      return;
    }
    document.add(
        new Paragraph(
            "Duration: "
                + (evidence.get("durationSeconds") == null
                    ? "UNKNOWN"
                    : str(evidence.get("durationSeconds")) + " seconds")
                + " · Source: "
                + orDash(str(evidence.get("durationSource"))),
            fonts.body));
    if (evidence.get("reasons") instanceof List<?> reasons) {
      for (Object reason : reasons) document.add(new Paragraph(str(reason), fonts.body));
    }
    if (evidence.get("dimensions") instanceof Map<?, ?> dimensions) {
      List<Map.Entry<?, ?>> rows = new ArrayList<>(dimensions.entrySet());
      rows.sort(
          java.util.Comparator.comparingInt(
              entry ->
                  entry.getValue() instanceof Map<?, ?> risk
                          && Boolean.TRUE.equals(risk.get("material"))
                      ? 0
                      : 1));
      for (Map.Entry<?, ?> entry : rows) {
        if (!(entry.getValue() instanceof Map<?, ?> risk)) continue;
        Paragraph heading =
            new Paragraph(str(entry.getKey()) + " · " + orDash(str(risk.get("level"))), fonts.bold);
        heading.setSpacingBefore(5);
        heading.add(new Chunk("\n" + orDash(str(risk.get("reason"))), fonts.body));
        heading.add(
            new Chunk(
                "\nEvidence: " + orDash(referenceText(risk.get("evidenceReferences"), null)),
                fonts.muted));
        heading.setKeepTogether(true);
        document.add(heading);
      }
    }
    if (evidence.get("durationLoad") instanceof Map<?, ?> load) {
      document.add(
          new Paragraph(
              "Duration load: "
                  + orDash(str(load.get("level")))
                  + " · "
                  + orDash(str(load.get("reason"))),
              fonts.body));
    }
    if (evidence.get("provenance") instanceof Map<?, ?> provenance) {
      document.add(
          new Paragraph(
              "Evaluator: "
                  + orDash(str(provenance.get("evaluatorVersion")))
                  + " · Source: "
                  + orDash(str(provenance.get("source"))),
              fonts.muted));
      if (provenance.get("sourceEvidence") instanceof Map<?, ?> source && !source.isEmpty()) {
        document.add(
            new Paragraph("Source evidence: " + orDash(str(source.get("source"))), fonts.muted));
        document.add(
            new Paragraph("Prompt hash: " + orDash(str(source.get("promptHash"))), fonts.muted));
        document.add(
            new Paragraph("Fixture: " + orDash(str(source.get("fixtureVersion"))), fonts.muted));
      }
    }
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
    columns.addCell(
        bulletColumn("Strengths", "✓", strings(assessment.get("strengths")), GREEN, fonts));
    columns.addCell(
        bulletColumn("Needs attention", "⚠", strings(assessment.get("concerns")), AMBER, fonts));
    columns.addCell(
        bulletColumn(
            "Recommended changes",
            "→",
            strings(assessment.get("recommended_changes")),
            BLUE,
            fonts));
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
      Paragraph family8Heading =
          new Paragraph(
              "Creative quality / Evidence completeness / Render authorization", fonts.bold);
      family8Heading.setSpacingBefore(6);
      family8Heading.setSpacingAfter(4);
      document.add(family8Heading);
      Map<?, ?> creative = family8.get("creativeQuality") instanceof Map<?, ?> map ? map : Map.of();
      Map<?, ?> evidence =
          family8.get("evidenceCompleteness") instanceof Map<?, ?> map ? map : Map.of();
      Map<?, ?> authorization =
          family8.get("renderAuthorization") instanceof Map<?, ?> map ? map : Map.of();
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
                        + orDash(
                            referenceText(
                                detail.get("references"), detail.get("evidenceReferences"))),
                    fonts.muted));
          }
        }
      }
    }

    addGeneralProducibility(document, assessment.get("general_producibility"), fonts);

    List<Map.Entry<?, ?>> applicabilityRows = new ArrayList<>();
    if (assessment.get("specialized_applicability") instanceof Map<?, ?> applicability) {
      for (Map.Entry<?, ?> entry : applicability.entrySet()) {
        if (entry.getValue() instanceof Map<?, ?>) {
          applicabilityRows.add(entry);
        }
      }
    }
    if (!applicabilityRows.isEmpty()) {
      applicabilityRows.sort((left, right) -> str(left.getKey()).compareTo(str(right.getKey())));
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
          detail.addElement(new Paragraph("What to change: " + clean(recommendation), fonts.small));
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
      head.add(
          new Chunk(
              clean(orDash(fix.severity())) + "  ",
              fonts.colored(fonts.bold, severityColor(fix.severity()))));
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
              orDash(provenance.semanticProvider())
                  + " / "
                  + orDash(provenance.semanticModelVersion()),
              fonts));
      document.add(
          labelled(
              "Versions: ",
              "parser "
                  + orDash(provenance.parserVersion())
                  + ", rule engine "
                  + orDash(provenance.ruleEngineVersion()),
              fonts));
    }
    if (!orEmpty(report.evidenceMissing()).isEmpty()) {
      document.add(
          labelled("Missing evidence: ", String.join(", ", report.evidenceMissing()), fonts));
    }
    if (!orEmpty(report.parserWarnings()).isEmpty()) {
      document.add(
          labelled("Parser warnings: ", String.join(" · ", report.parserWarnings()), fonts));
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
      table.addCell(
          cell(
              orDash(rule.severity()),
              fonts.colored(fonts.small, severityColor(rule.severity())),
              null));
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
                      value == null ? "N/A" : String.format(Locale.ROOT, "%.0f", value),
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
        table.addCell(
            cell(
                oneDecimal(beat.startTime()) + "s - " + oneDecimal(beat.endTime()) + "s",
                fonts.small,
                null));
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
            cell(
                oneDecimal(segment.startTime()) + "s - " + oneDecimal(segment.endTime()) + "s",
                fonts.small,
                null));
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
            "  ·  " + clean(orDash(rule.ruleId())) + "  ·  " + clean(orDash(rule.message())),
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
            "DejaVuSans-Bold.ttf",
            BaseFont.IDENTITY_H,
            BaseFont.EMBEDDED,
            true,
            boldFontBytes,
            null);
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
          new Phrase("Pompom Creative Intelligence  ·  Page " + writer.getPageNumber(), font);
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
