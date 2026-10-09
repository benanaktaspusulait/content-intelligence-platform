package com.pompomhills.intelligence.video.api;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.List;
import java.util.Map;
import org.openpdf.text.Document;
import org.openpdf.text.DocumentException;
import org.openpdf.text.Font;
import org.openpdf.text.PageSize;
import org.openpdf.text.Paragraph;
import org.openpdf.text.Phrase;
import org.openpdf.text.Rectangle;
import org.openpdf.text.pdf.BaseFont;
import org.openpdf.text.pdf.PdfPCell;
import org.openpdf.text.pdf.PdfPTable;
import org.openpdf.text.pdf.PdfWriter;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

/** Backend-rendered, human-readable report for a completed visual-motion analysis. */
@Service
public class VideoAnalysisPdfService {
  private static final Color INK = new Color(0x17, 0x21, 0x1b);
  private static final Color MUTED = new Color(0x5f, 0x6b, 0x63);
  private static final Color MOSS = new Color(0x29, 0x43, 0x32);
  private static final Color PALE = new Color(0xf0, 0xf2, 0xeb);
  private final byte[] regularBytes = readFont("fonts/DejaVuSans.ttf");
  private final byte[] boldBytes = readFont("fonts/DejaVuSans-Bold.ttf");

  public byte[] render(String title, VideoDtos.AnalysisStatusResponse status) {
    if (!status.hasCompletedAnalysis()) throw new IllegalArgumentException("A completed analysis is required before exporting a PDF");
    try {
      Fonts fonts = fonts();
      ByteArrayOutputStream out = new ByteArrayOutputStream();
      Document document = new Document(PageSize.A4, 34, 34, 36, 42);
      PdfWriter.getInstance(document, out);
      document.addTitle(clean(title) + " - Visual analysis report");
      document.addCreator("Pompom Creative Intelligence");
      document.open();
      document.add(new Paragraph(clean(title), fonts.title));
      document.add(new Paragraph("VISUAL MOTION ANALYSIS  ·  " + clean(status.analysisVersion()), fonts.kicker));
      document.add(new Paragraph("A measured, duration-aware view of motion, sampling quality and observed visual structure. Audience performance and retention are not inferred.", fonts.body));
      document.add(summaryCards(status, fonts));
      section(document, "Executive reading", fonts);
      document.add(new Paragraph(clean(orDash(status.reason())), fonts.body));
      document.add(assessmentTable(status, fonts));
      section(document, "Motion profile by time", fonts);
      document.add(new Paragraph("Each bar is the normalized average visual change in that segment. Exact time boundaries and measurement coverage remain visible.", fonts.muted));
      document.add(segmentTable(status, fonts));
      section(document, "Measurement quality", fonts);
      document.add(metricsTable(status, fonts));
      section(document, "Observed visual beats", fonts);
      document.add(beatTable(status, fonts));
      section(document, "Evidence limits", fonts);
      document.add(new Paragraph("The report separates what was measured from what remains unknown. These limits prevent motion evidence from being read as a platform or audience outcome.", fonts.body));
      addBullet(document, "Plan fidelity: " + value(map(map(status.temporalProfile()).get("planRenderFidelity")), "status"), fonts);
      addBullet(document, "Semantic evidence coverage: " + value(map(status.semanticVideoEvidence()), "semanticCoverage"), fonts);
      addBullet(document, "No imported retention curve, audience metric or platform outcome is used.", fonts);
      document.add(new Paragraph("Source analysis ID: " + clean(orDash(status.analysisId() == null ? null : status.analysisId().toString())), fonts.muted));
      document.close();
      return out.toByteArray();
    } catch (DocumentException | IOException error) {
      throw new IllegalStateException("Video analysis PDF could not be rendered", error);
    }
  }

  private PdfPTable summaryCards(VideoDtos.AnalysisStatusResponse status, Fonts f) throws DocumentException {
    PdfPTable table = new PdfPTable(4); table.setWidthPercentage(100); table.setSpacingBefore(14); table.setSpacingAfter(14);
    addCard(table, "CLASSIFICATION", status.classification(), f);
    addCard(table, "MOTION SCORE", score(status.motionHeuristicScore()), f);
    addCard(table, "MEASUREMENT CONFIDENCE", percent(status.measurementConfidence()), f);
    addCard(table, "TIMELINE COVERAGE", percent(number(map(status.measurementQuality()).get("timelineCoverage"))), f);
    return table;
  }
  private void addCard(PdfPTable table, String label, String value, Fonts f) {
    PdfPCell cell = new PdfPCell(); cell.setBackgroundColor(PALE); cell.setBorderColor(new Color(0xd9,0xde,0xd7)); cell.setPadding(9);
    cell.addElement(new Paragraph(label, f.kicker)); cell.addElement(new Paragraph(clean(orDash(value)), f.card)); table.addCell(cell);
  }
  private PdfPTable assessmentTable(VideoDtos.AnalysisStatusResponse status, Fonts f) throws DocumentException {
    PdfPTable table = table(3); header(table, List.of("Dimension", "Result", "What the evidence supports"), f);
    Map<String,Object> temporal = map(status.temporalProfile());
    addRow(table, "Hook", value(map(temporal.get("hook")), "status"), "Opening visual activity; semantic readability is shown separately.", f);
    addRow(table, "Payoff", value(map(temporal.get("payoff")), "status"), "Motion and semantic ending evidence where available.", f);
    addRow(table, "Loop", value(map(temporal.get("loop")), "status"), "Endpoint similarity and continuity evidence; not a retention claim.", f);
    return table;
  }
  private PdfPTable segmentTable(VideoDtos.AnalysisStatusResponse status, Fonts f) throws DocumentException {
    PdfPTable table = table(5); header(table, List.of("Segment", "Time", "Avg motion", "Profile", "Coverage"), f);
    List<Map<String,Object>> segments = list(map(status.temporalProfile()).get("segments"));
    if (segments.isEmpty()) { addRow(table, "—", "No segment profile returned", "—", "—", f); return table; }
    for (Map<String,Object> segment : segments) {
      table.addCell(cell("S" + integer(segment.get("segmentIndex")), f.body));
      table.addCell(cell(decimal(segment.get("startSeconds")) + "–" + decimal(segment.get("endSeconds")) + "s", f.body));
      table.addCell(cell(percent(number(segment.get("averageMotion"))), f.body));
      table.addCell(new PdfPCell(bar(number(segment.get("averageMotion")), f)));
      table.addCell(cell(percent(number(segment.get("coverage"))), f.body));
    }
    return table;
  }
  private PdfPTable metricsTable(VideoDtos.AnalysisStatusResponse status, Fonts f) throws DocumentException {
    PdfPTable table = table(3); header(table, List.of("Metric", "Measured value", "Interpretation"), f);
    Map<String,Object> q = map(status.measurementQuality()); Map<String,Object> m = map(status.motion()); Map<String,Object> s = map(status.sampling());
    addRow(table, "Valid frame pairs", String.valueOf(q.getOrDefault("validPairCount", "—")), "Decoded frame-pair measurements.", f);
    addRow(table, "Decode success", percent(number(q.get("decodeSuccessRatio"))), "Media decode and sampling quality only.", f);
    addRow(table, "Opening motion", percent(number(m.get("openingMotionIntensity"))), "Visual change in the opening window.", f);
    addRow(table, "Overall motion", percent(number(m.get("overallMotionIntensity"))), "Duration-weighted visual change.", f);
    addRow(table, "Ending motion", percent(number(m.get("endingMotionEvidence"))), "Visual change in the ending window.", f);
    addRow(table, "Requested / decoded", String.valueOf(s.getOrDefault("requestedSamples", "—")) + " / " + String.valueOf(s.getOrDefault("decodedSamples", "—")), "Sampling transport result.", f);
    return table;
  }
  private PdfPTable beatTable(VideoDtos.AnalysisStatusResponse status, Fonts f) throws DocumentException {
    PdfPTable table = table(4); header(table, List.of("Beat", "Time", "Observed action", "Consequence / state"), f);
    List<Map<String,Object>> beats = list(map(status.semanticVideoEvidence()).get("beats"));
    if (beats.isEmpty()) { addRow(table, "—", "No semantic beat record", "—", "—", f); return table; }
    for (Map<String,Object> beat : beats) addRow(table, "Beat " + integer(beat.get("beatIndex")), decimal(beat.get("startSeconds")) + "–" + decimal(beat.get("endSeconds")) + "s", value(beat, "primaryAction") + " · " + value(beat, "targetObject"), value(beat, "consequence") + " · " + value(beat, "characterStateAfter"), f);
    return table;
  }
  private PdfPTable bar(double ratio, Fonts f) throws DocumentException {
    double bounded = Math.max(0.02, Math.min(1.0, ratio));
    PdfPTable bar = new PdfPTable(2); bar.setWidthPercentage(100); bar.setWidths(new float[] {(float) bounded, (float) (1 - bounded)});
    PdfPCell fill = new PdfPCell(new Phrase(" ", f.body)); fill.setBackgroundColor(MOSS); fill.setBorder(Rectangle.NO_BORDER); fill.setFixedHeight(8);
    PdfPCell rest = new PdfPCell(new Phrase(" ", f.body)); rest.setBackgroundColor(new Color(0xe1,0xe6,0xdf)); rest.setBorder(Rectangle.NO_BORDER); rest.setFixedHeight(8);
    bar.addCell(fill); bar.addCell(rest); return bar;
  }
  private static PdfPTable table(int columns) { PdfPTable table = new PdfPTable(columns); table.setWidthPercentage(100); table.setSpacingAfter(9); return table; }
  private static void header(PdfPTable table, List<String> labels, Fonts f) { for (String label : labels) { PdfPCell cell = cell(label, f.kickerLight); cell.setBackgroundColor(MOSS); table.addCell(cell); } }
  private static void addRow(PdfPTable table, String a, String b, String c, Fonts f) { table.addCell(cell(a,f.body)); table.addCell(cell(b,f.body)); table.addCell(cell(c,f.body)); }
  private static void addRow(PdfPTable table, String a, String b, String c, String d, Fonts f) { table.addCell(cell(a,f.body)); table.addCell(cell(b,f.body)); table.addCell(cell(c,f.body)); table.addCell(cell(d,f.body)); }
  private static PdfPCell cell(String value, Font font) { PdfPCell cell = new PdfPCell(new Phrase(clean(value), font)); cell.setPadding(5); cell.setBorderColor(new Color(0xd9,0xde,0xd7)); return cell; }
  private static void section(Document document, String title, Fonts f) throws DocumentException { document.add(new Paragraph(title, f.heading)); }
  private static void addBullet(Document document, String text, Fonts f) throws DocumentException { document.add(new Paragraph("• " + clean(text), f.body)); }
  private static String value(Map<String,Object> map, String key) { return map.isEmpty() ? "—" : String.valueOf(map.getOrDefault(key, "—")); }
  private static String value(Object value) { return value == null ? "—" : String.valueOf(value); }
  @SuppressWarnings("unchecked") private static Map<String,Object> map(Object value) { return value instanceof Map<?,?> m ? (Map<String,Object>) m : Map.of(); }
  private static List<Map<String,Object>> list(Object value) { if (!(value instanceof List<?> values)) return List.of(); return values.stream().filter(item -> item instanceof Map<?,?>).map(VideoAnalysisPdfService::map).toList(); }
  private static double number(Object value) { return value instanceof Number n ? n.doubleValue() : 0.0; }
  private static String percent(Double value) { return value == null ? "—" : percent(value.doubleValue()); }
  private static String percent(double value) { return String.format(java.util.Locale.ROOT, "%.1f%%", value * 100); }
  private static String score(Double value) { return value == null ? "—" : String.format(java.util.Locale.ROOT, "%.1f / 100", value); }
  private static String decimal(Object value) { return value instanceof Number n ? String.format(java.util.Locale.ROOT, "%.2f", n.doubleValue()) : "—"; }
  private static String integer(Object value) { return value instanceof Number n ? String.valueOf(n.intValue()) : "—"; }
  private static String orDash(String value) { return value == null || value.isBlank() ? "—" : value; }
  private static String clean(String value) { return value == null ? "" : value.replaceAll("[\\x{10000}-\\x{10FFFF}\\uFE0F\\u200D\\p{Cc}&&[^\\n\\t]]", ""); }
  private static byte[] readFont(String path) { try (InputStream input = new ClassPathResource(path).getInputStream()) { return input.readAllBytes(); } catch (IOException error) { throw new IllegalStateException("Missing PDF font resource: " + path, error); } }
  private Fonts fonts() throws DocumentException, IOException { return new Fonts(BaseFont.createFont("DejaVuSans.ttf", BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, regularBytes, null), BaseFont.createFont("DejaVuSans-Bold.ttf", BaseFont.IDENTITY_H, BaseFont.EMBEDDED, true, boldBytes, null)); }
  private record Fonts(BaseFont regular, BaseFont bold, Font title, Font kicker, Font kickerLight, Font heading, Font body, Font muted, Font card) {
    Fonts(BaseFont regular, BaseFont bold) { this(regular, bold, new Font(bold, 19, Font.BOLD, INK), new Font(bold, 7, Font.BOLD, MOSS), new Font(bold, 7, Font.BOLD, Color.WHITE), new Font(bold, 13, Font.BOLD, INK), new Font(regular, 8.5f, Font.NORMAL, INK), new Font(regular, 8, Font.NORMAL, MUTED), new Font(bold, 13, Font.BOLD, INK)); }
  }
}
