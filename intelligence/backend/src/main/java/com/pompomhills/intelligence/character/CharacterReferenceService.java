package com.pompomhills.intelligence.character;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class CharacterReferenceService {
  private static final long MAX_BYTES = 15L * 1024 * 1024;
  private final JdbcClient jdbc;
  private final CharacterRepository characters;
  private final Path dataRoot;

  public CharacterReferenceService(JdbcClient jdbc, CharacterRepository characters,
      @Value("${pompom.data-root:/tmp/pompom-data}") String dataRoot) {
    this.jdbc = jdbc;
    this.characters = characters;
    this.dataRoot = Path.of(dataRoot).toAbsolutePath().normalize();
  }

  @Transactional(readOnly = true)
  public List<Map<String, Object>> list(UUID characterId) {
    requireCharacter(characterId);
    var rows = jdbc.sql("SELECT id::text id,relative_path,description,sha256,approval_status,version_number,created_at,approved_at,approved_by FROM character_references WHERE character_id=:character ORDER BY created_at DESC,id")
        .param("character", characterId)
        .query((rs, row) -> Map.<String, Object>ofEntries(
            Map.entry("id", rs.getString("id")), Map.entry("relativePath", rs.getString("relative_path")),
            Map.entry("description", rs.getString("description") == null ? "" : rs.getString("description")),
            Map.entry("sha256", rs.getString("sha256") == null ? "" : rs.getString("sha256")),
            Map.entry("status", rs.getString("approval_status")), Map.entry("approvalStatus", rs.getString("approval_status")),
            Map.entry("version", rs.getInt("version_number")),
            Map.entry("createdAt", rs.getTimestamp("created_at").toInstant().toString()),
            Map.entry("approvedAt", rs.getTimestamp("approved_at") == null ? "" : rs.getTimestamp("approved_at").toInstant().toString()),
            Map.entry("approvedBy", rs.getString("approved_by") == null ? "" : rs.getString("approved_by")))).list();
    return rows.stream().map(row -> {
      var result = new java.util.LinkedHashMap<String, Object>(row);
      if ("APPROVED".equals(row.get("status"))) {
        try { imagePath(characterId, UUID.fromString(String.valueOf(row.get("id")))); }
        catch (IllegalArgumentException invalid) { result.put("status", "STALE"); }
      }
      return (Map<String, Object>) result;
    }).toList();
  }

  @Transactional(readOnly = true)
  public Path imagePath(UUID characterId, UUID referenceId) {
    requireCharacter(characterId);
    var stored = jdbc.sql("SELECT relative_path,sha256 FROM character_references WHERE id=:id AND character_id=:character")
        .param("id", referenceId).param("character", characterId)
        .query((rs, row) -> Map.of("path", rs.getString("relative_path"), "sha", rs.getString("sha256")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Character reference not found"));
    Path path = dataRoot.resolve(String.valueOf(stored.get("path"))).normalize();
    if (!path.startsWith(dataRoot) || !Files.isRegularFile(path)) throw new IllegalArgumentException("Reference image is missing");
    try {
      String current = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
      if (!current.equals(stored.get("sha"))) throw new IllegalArgumentException("Reference image hash no longer matches the approved record");
      return path;
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to verify character reference", error);
    }
  }

  @Transactional
  public Map<String, Object> upload(UUID characterId, MultipartFile file, String description) {
    requireCharacter(characterId);
    if (file == null || file.isEmpty() || file.getSize() > MAX_BYTES)
      throw new IllegalArgumentException("Choose a non-empty image smaller than 15 MB");
    try {
      byte[] bytes = file.getBytes();
      String extension = imageExtension(bytes);
      String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
      Path folder = dataRoot.resolve("character-references").resolve(characterId.toString()).normalize();
      if (!folder.startsWith(dataRoot)) throw new IllegalArgumentException("Invalid character reference path");
      Files.createDirectories(folder);
      Path target = folder.resolve(sha + "." + extension).normalize();
      if (!target.startsWith(dataRoot)) throw new IllegalArgumentException("Invalid character reference path");
      if (!Files.exists(target)) Files.write(target, bytes);
      String relative = dataRoot.relativize(target).toString().replace('\\', '/');
      UUID id = UUID.randomUUID();
      int version = jdbc.sql("SELECT COALESCE(MAX(version_number),0)+1 FROM character_references WHERE character_id=:character")
          .param("character", characterId).query(Integer.class).single();
      jdbc.sql("INSERT INTO character_references(id,character_id,relative_path,description,sha256,approval_status,version_number) VALUES (:id,:character,:path,:description,:sha,'PENDING_REVIEW',:version)")
          .param("id", id).param("character", characterId).param("path", relative)
          .param("description", description == null ? "" : description.trim()).param("sha", sha).param("version", version).update();
      return Map.of("id", id.toString(), "relativePath", relative, "sha256", sha,
          "version", version, "status", "PENDING_REVIEW", "providerCallPerformed", false);
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to store character reference", error);
    }
  }

  @Transactional
  public Map<String, Object> approve(UUID characterId, UUID referenceId, String reviewer) {
    requireCharacter(characterId);
    if (reviewer == null || reviewer.isBlank()) throw new IllegalArgumentException("Reviewer name is required");
    var ref = jdbc.sql("SELECT relative_path,sha256,approval_status FROM character_references WHERE id=:id AND character_id=:character")
        .param("id", referenceId).param("character", characterId)
        .query((rs, row) -> Map.of("path", rs.getString("relative_path"), "sha", rs.getString("sha256"), "status", rs.getString("approval_status")))
        .optional().orElseThrow(() -> new IllegalArgumentException("Character reference not found"));
    String sha = String.valueOf(ref.get("sha"));
    Path target = dataRoot.resolve(String.valueOf(ref.get("path"))).normalize();
    if (!target.startsWith(dataRoot) || !Files.isRegularFile(target)) throw new IllegalArgumentException("Reference image is missing from local storage");
    try {
      String current = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(target)));
      if (!current.equals(sha)) throw new IllegalArgumentException("Reference image changed after upload; upload it again before approval");
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Unable to verify character reference", error);
    }
    Instant now = Instant.now();
    jdbc.sql("UPDATE character_references SET approval_status='APPROVED',approved_at=:at,approved_by=:reviewer WHERE id=:id")
        .param("at", java.time.OffsetDateTime.ofInstant(now, java.time.ZoneOffset.UTC)).param("reviewer", reviewer.trim()).param("id", referenceId).update();
    return Map.of("id", referenceId.toString(), "sha256", sha, "status", "APPROVED", "approvedAt", now.toString(), "approvedBy", reviewer.trim());
  }

  private void requireCharacter(UUID id) {
    if (!characters.existsById(id)) throw new IllegalArgumentException("Character not found: " + id);
  }

  private String imageExtension(byte[] bytes) {
    if (bytes.length >= 24 && bytes[0] == (byte)0x89 && bytes[1] == 'P' && bytes[2] == 'N' && bytes[3] == 'G'
        && bytes[12] == 'I' && bytes[13] == 'H' && bytes[14] == 'D' && bytes[15] == 'R') {
      int width = java.nio.ByteBuffer.wrap(bytes, 16, 4).getInt();
      int height = java.nio.ByteBuffer.wrap(bytes, 20, 4).getInt();
      if (width > 0 && height > 0 && width <= 8192 && height <= 8192) return "png";
    }
    if (bytes.length > 128 && bytes[0] == (byte)0xff && bytes[1] == (byte)0xd8 && bytes[2] == (byte)0xff
        && bytes[bytes.length - 2] == (byte)0xff && bytes[bytes.length - 1] == (byte)0xd9) return "jpg";
    if (bytes.length >= 20 && bytes[0] == 'R' && bytes[1] == 'I' && bytes[2] == 'F' && bytes[3] == 'F'
        && bytes[8] == 'W' && bytes[9] == 'E' && bytes[10] == 'B' && bytes[11] == 'P') return "webp";
    throw new IllegalArgumentException("Only valid PNG, JPEG or WebP images can be uploaded");
  }
}
