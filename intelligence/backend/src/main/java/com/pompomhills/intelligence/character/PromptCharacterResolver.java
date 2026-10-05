package com.pompomhills.intelligence.character;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

@Service
public class PromptCharacterResolver {
  public static final String VERSION = "prompt-character-resolver-v1";
  private final JdbcClient jdbc;

  public PromptCharacterResolver(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  public List<DetectedCharacter> resolve(String promptText) {
    if (promptText == null || promptText.isBlank()) return List.of();
    List<DetectedCharacter> detected = new ArrayList<>();
    jdbc.sql("""
        SELECT c.id,c.name,c.active,COALESCE(string_agg(ca.alias, '|' ORDER BY ca.alias), '') aliases
        FROM characters c LEFT JOIN character_aliases ca ON ca.character_id=c.id
        WHERE c.active=true GROUP BY c.id,c.name,c.active ORDER BY c.name
        """).query((rs, ignored) -> {
      String canonical = rs.getString("name");
      List<String> aliases = new ArrayList<>();
      aliases.add(canonical);
      String rawAliases = rs.getString("aliases");
      if (rawAliases != null && !rawAliases.isBlank()) {
        for (String alias : rawAliases.split("\\|")) if (!alias.isBlank()) aliases.add(alias);
      }
      String matched = aliases.stream().filter(alias -> tokenPattern(alias).matcher(promptText).find()).findFirst().orElse(null);
      if (matched == null) return null;
      int mentions = count(tokenPattern(matched), promptText);
      return new DetectedCharacter(rs.getObject("id", java.util.UUID.class), canonical, matched, mentions,
          "UNKNOWN", "UNKNOWN", "PROMPT_FILE");
    }).list().stream().filter(java.util.Objects::nonNull).forEach(detected::add);
    return detected;
  }

  private Pattern tokenPattern(String value) {
    return Pattern.compile("(?iu)(?<![\\p{L}\\p{N}_])" + Pattern.quote(value.trim()) + "(?![\\p{L}\\p{N}_])");
  }

  private int count(Pattern pattern, String text) {
    int count = 0; Matcher matcher = pattern.matcher(text); while (matcher.find()) count++; return count;
  }

  public record DetectedCharacter(java.util.UUID characterId, String canonicalName, String matchedAlias,
      int mentionCount, String participation, String role, String evidenceSource) {}
}
