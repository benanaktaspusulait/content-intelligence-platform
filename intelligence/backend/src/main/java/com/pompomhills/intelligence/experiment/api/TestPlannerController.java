package com.pompomhills.intelligence.experiment.api;

import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/test-planner")
public class TestPlannerController {
  private final JdbcClient jdbc;

  public TestPlannerController(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @GetMapping
  PlannerView plan() {
    Map<String, Integer> counts =
        jdbc
            .sql(
                """
                SELECT experiment_type,count(*) AS total
                FROM experiments GROUP BY experiment_type
                """)
            .query((rs, ignored) -> Map.entry(rs.getString("experiment_type"), rs.getInt("total")))
            .list()
            .stream()
            .collect(java.util.stream.Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    int charactersWithoutTests =
        jdbc.sql(
                """
                SELECT count(*) FROM characters c
                WHERE active=true AND NOT EXISTS (
                  SELECT 1 FROM video_characters vc
                  JOIN experiments e ON e.video_id=vc.video_id
                  WHERE vc.character_id=c.id)
                """)
            .query(Integer.class)
            .single();
    return new PlannerView(
        Map.of("EXPLOIT", 60, "ADJACENT", 20, "EXPLORE", 20),
        counts,
        charactersWithoutTests,
        List.of(
            "Register one primary metric before publication",
            "Change one creative variable per controlled test",
            "Reserve exploration capacity for under-tested characters"));
  }

  public record PlannerView(
      Map<String, Integer> recommendedAllocation,
      Map<String, Integer> currentExperimentCounts,
      int charactersWithoutTests,
      List<String> guardrails) {}
}
