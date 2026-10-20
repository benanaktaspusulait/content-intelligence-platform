package com.pompomhills.intelligence.character;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Resolves a selected protagonist against the canonical character registry. */
public final class CanonicalCharacterIdentity {
  private static final Set<String> CHARACTER_DETERMINERS = Set.of("the", "a", "an");
  private static final Pattern NAMED_SPECIES =
      Pattern.compile(
          "(?u)\\b([\\p{Lu}][\\p{L}’'-]{1,40})\\s*,?\\s+(?:the\\s+)?(?i:rabbit|bunny|bear|cat|dog|fox|hedgehog|crocodile)\\b");

  private final JdbcClient jdbc;

  public CanonicalCharacterIdentity(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  public Map<String, Object> requireActive(String rawId, String submittedName) {
    if (jdbc == null || rawId == null || rawId.isBlank())
      throw new IllegalArgumentException("Select a registered canonical main character before creating a story");
    UUID id;
    try {
      id = UUID.fromString(rawId);
    } catch (IllegalArgumentException invalid) {
      throw new IllegalArgumentException("A registered canonical character ID is required", invalid);
    }
    var character =
        jdbc.sql("SELECT id::text id,name,status,notes,active FROM characters WHERE id=:id AND active=true")
            .param("id", id)
            .query(
                (rs, ignored) ->
                    Map.<String, Object>of(
                        "id", rs.getString("id"),
                        "name", rs.getString("name"),
                        "status", rs.getString("status"),
                        "notes", rs.getString("notes") == null ? "" : rs.getString("notes"),
                        "active", rs.getBoolean("active")))
            .optional()
            .orElseThrow(() -> new IllegalArgumentException("Selected character is not active in the canonical registry"));
    if (submittedName != null
        && !submittedName.isBlank()
        && !submittedName.trim().equalsIgnoreCase(String.valueOf(character.get("name"))))
      throw new IllegalArgumentException("Selected character ID and name do not match the canonical registry");
    return character;
  }

  public List<Map<String, Object>> activeRegistry() {
    if (jdbc == null) throw new IllegalArgumentException("Canonical character registry is unavailable");
    return jdbc.sql("SELECT id::text id,name FROM characters WHERE active=true ORDER BY name")
        .query((rs, ignored) -> Map.<String, Object>of("id", rs.getString("id"), "name", rs.getString("name")))
        .list();
  }

  public static void requireStoryIdentity(String text, Map<String, Object> character, List<Map<String, Object>> registry) {
    if (text == null || text.isBlank() || character == null || character.isEmpty())
      throw new IllegalArgumentException("Canonical main character and story text are required");
    String expected = String.valueOf(character.get("name"));
    Pattern expectedName = Pattern.compile("(?iu)(?<![\\p{L}\\p{N}_])" + Pattern.quote(expected) + "(?![\\p{L}\\p{N}_])");
    if (!expectedName.matcher(text).find())
      throw new IllegalArgumentException("Story text does not use the selected canonical protagonist: " + expected);
    var known = registry.stream().map(row -> String.valueOf(row.get("name")).toLowerCase(java.util.Locale.ROOT)).collect(java.util.stream.Collectors.toSet());
    Matcher declared = NAMED_SPECIES.matcher(text);
    while (declared.find()) {
      String name = declared.group(1);
      if (CHARACTER_DETERMINERS.contains(name.toLowerCase(java.util.Locale.ROOT))) continue;
      if (!known.contains(name.toLowerCase(java.util.Locale.ROOT)))
        throw new IllegalArgumentException("Unregistered named protagonist or character in story: " + name);
    }
  }
}
