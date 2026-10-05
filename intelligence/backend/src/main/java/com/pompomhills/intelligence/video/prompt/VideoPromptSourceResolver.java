package com.pompomhills.intelligence.video.prompt;

import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.video.VideoEntity;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

@Service
public class VideoPromptSourceResolver {
  public static final String VERSION = "video-prompt-source-resolver-v1";
  private static final long MAX_PROMPT_BYTES = 1024L * 1024L;
  private static final List<String> EXTENSIONS = List.of(".txt", ".md", ".json", ".yaml", ".yml");
  private final PompomProperties properties;
  private final JdbcClient jdbc;

  public VideoPromptSourceResolver(PompomProperties properties, JdbcClient jdbc) {
    this.properties = properties;
    this.jdbc = jdbc;
  }

  public PromptSourceResolution resolve(VideoEntity video) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    Path file = root.resolve(video.getRelativePath()).normalize();
    if (!file.startsWith(root) || !Files.isRegularFile(file)) {
      return result(PromptSourceResolution.Status.NOT_FOUND, video.getRelativePath(), null, null,
          "SOURCE_FOLDER_MISSING", "UNKNOWN", 0, List.of(), "Video source file is unavailable");
    }
    Path folder = file.getParent();
    if (folder == null || !Files.isDirectory(folder)) {
      return result(PromptSourceResolution.Status.NOT_FOUND, video.getRelativePath(), null, null,
          "SOURCE_FOLDER_MISSING", "UNKNOWN", 0, List.of(), "Video source folder is unavailable");
    }
    try {
      List<Path> prompts = eligiblePromptFiles(folder);
      String stem = normalizeStem(stripExtension(file.getFileName().toString()));
      List<Path> exact = prompts.stream().filter(candidate -> isExactCandidate(stem, candidate)).toList();
      if (!exact.isEmpty()) return read(video, exact.get(0), PromptSourceResolution.Status.MATCHED_SIDECAR, "EXACT_SIDECAR", "HIGH", prompts);
      long videoCount;
      try (Stream<Path> files = Files.list(folder)) {
        videoCount = files.filter(Files::isRegularFile).filter(this::isVideo).count();
      }
      if (prompts.size() == 1 && videoCount == 1) {
        return read(video, prompts.get(0), PromptSourceResolution.Status.MATCHED_SINGLE_FOLDER_PROMPT,
            "SINGLE_FOLDER_PROMPT", "MEDIUM", prompts);
      }
      if (prompts.size() > 1) {
        return result(PromptSourceResolution.Status.AMBIGUOUS, video.getRelativePath(), null, null,
            "MULTIPLE_PROMPT_CANDIDATES", "UNKNOWN", prompts.size(), relative(root, prompts),
            "Multiple prompt files could describe this video");
      }
      return result(PromptSourceResolution.Status.NOT_FOUND, video.getRelativePath(), null, null,
          "NO_PROMPT_FILE", "UNKNOWN", 0, List.of(), "No eligible prompt file was found");
    } catch (IOException error) {
      return result(PromptSourceResolution.Status.ERROR, video.getRelativePath(), null, null,
          "FILESYSTEM_ERROR", "UNKNOWN", 0, List.of(), error.getMessage());
    }
  }

  private PromptSourceResolution read(VideoEntity video, Path path, PromptSourceResolution.Status status,
      String method, String confidence, List<Path> candidates) {
    Path root = properties.dataRoot().toAbsolutePath().normalize();
    String promptPath = relative(root, path).get(0);
    try {
      if (Files.size(path) > MAX_PROMPT_BYTES) {
        return result(PromptSourceResolution.Status.ERROR, video.getRelativePath(), promptPath, null,
            method, "UNKNOWN", candidates.size(), relative(root, candidates), "Prompt file exceeds size limit");
      }
      String text = jdbc.sql("SELECT raw_text FROM prompt_versions WHERE source_path=:path ORDER BY version_number DESC LIMIT 1")
          .param("path", promptPath).query(String.class).optional().orElseGet(() -> {
            try { return Files.readString(path, StandardCharsets.UTF_8); }
            catch (IOException error) { throw new IllegalStateException(error); }
          });
      return new PromptSourceResolution(status, video.getRelativePath(), promptPath, text, method,
          confidence, candidates.size(), relative(root, candidates), null);
    } catch (RuntimeException | IOException error) {
      return result(PromptSourceResolution.Status.ERROR, video.getRelativePath(), promptPath, null,
          method, "UNKNOWN", candidates.size(), relative(root, candidates), error.getMessage());
    }
  }

  private List<Path> eligiblePromptFiles(Path folder) throws IOException {
    try (Stream<Path> files = Files.list(folder)) {
      return files.filter(Files::isRegularFile).filter(this::isPrompt).sorted(Comparator.comparing(Path::toString)).toList();
    }
  }

  private boolean isPrompt(Path file) {
    String name = file.getFileName().toString().toLowerCase(Locale.ROOT);
    return EXTENSIONS.stream().anyMatch(name::endsWith)
        && !name.contains("image") && !name.contains("storyboard")
        && !name.endsWith(".jsonl");
  }

  private boolean isVideo(Path file) {
    String name = file.getFileName().toString().toLowerCase(Locale.ROOT);
    return properties.allowedVideoExtensions().stream().anyMatch(extension -> name.endsWith("." + extension));
  }

  private boolean isExactCandidate(String videoStem, Path candidate) {
    String promptStem = normalizeStem(stripExtension(candidate.getFileName().toString()));
    if (promptStem.equals(videoStem)) return true;
    return promptStem.equals(videoStem + "prompt") || promptStem.equals(videoStem + "prompts");
  }

  private String normalizeStem(String value) {
    String normalized = value.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]+", "_");
    boolean changed;
    do {
      String next = normalized.replaceFirst("(_prompt|-prompt|_final|-final|_hd|_original)$", "");
      changed = !next.equals(normalized);
      normalized = next;
    } while (changed);
    return normalized.replaceAll("_+", "_").replaceAll("^_|_$", "");
  }

  private String stripExtension(String name) { int dot = name.lastIndexOf('.'); return dot < 0 ? name : name.substring(0, dot); }
  private List<String> relative(Path root, List<Path> paths) { return paths.stream().map(path -> root.relativize(path).toString().replace('\\', '/')).toList(); }
  private List<String> relative(Path root, Path path) { return List.of(root.relativize(path).toString().replace('\\', '/')); }
  private PromptSourceResolution result(PromptSourceResolution.Status status, String video, String prompt, String text,
      String method, String confidence, int count, List<String> candidates, String error) {
    return new PromptSourceResolution(status, video, prompt, text, method, confidence, count, candidates, error);
  }
}
