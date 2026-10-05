package com.pompom.creative.postrender;

import com.pompom.creative.domain.RenderJob;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/** Resolves payoff timing only from explicit, timestamped prompt declarations. */
@Component
public class PayoffWindowResolver {
  private static final Pattern RANGE = Pattern.compile(
      "(?i)(\\d+(?:\\.\\d+)?)\\s*s?\\s*(?:-|–|—|to)\\s*(\\d+(?:\\.\\d+)?)\\s*s?");
  private static final Pattern MARKER = Pattern.compile(
      "(?i)\\b(payoff|final payoff|punchline|reveal|ending|resolution|payoff beat)\\b");

  public PayoffWindow resolve(RenderJob job) {
    String prompt = job == null ? null : job.getPromptTextSnapshot();
    if (prompt == null || prompt.isBlank()) {
      return new PayoffWindow(PayoffWindowStatus.NOT_AVAILABLE, null, null,
          "PROMPT_SNAPSHOT", "No prompt snapshot is available.");
    }
    List<PayoffWindow> candidates = new ArrayList<>();
    for (String line : prompt.split("\\R")) {
      if (!MARKER.matcher(line).find()) continue;
      Matcher matcher = RANGE.matcher(line);
      while (matcher.find()) {
        double start = Double.parseDouble(matcher.group(1));
        double end = Double.parseDouble(matcher.group(2));
        if (end > start) {
          candidates.add(new PayoffWindow(PayoffWindowStatus.RESOLVED, start, end,
              "PROMPT_SNAPSHOT_EXPLICIT_MARKER", "Explicit timestamped payoff marker."));
        }
      }
    }
    if (candidates.size() == 1) return candidates.getFirst();
    if (candidates.size() > 1) {
      return new PayoffWindow(PayoffWindowStatus.AMBIGUOUS, null, null,
          "PROMPT_SNAPSHOT_EXPLICIT_MARKER", "Multiple payoff windows were declared.");
    }
    return new PayoffWindow(PayoffWindowStatus.NOT_AVAILABLE, null, null,
        "PROMPT_SNAPSHOT", "No explicit timestamped payoff marker was found.");
  }
}
