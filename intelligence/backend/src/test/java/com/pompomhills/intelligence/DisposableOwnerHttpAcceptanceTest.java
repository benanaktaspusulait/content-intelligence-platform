package com.pompomhills.intelligence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.security.Permission;
import java.security.SecureRandom;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.ScheduledAnnotationBeanPostProcessor;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/** The harness starts the existing FastAPI fixture transport. Every application operation below
 * goes over a real random-port Tomcat socket and the unmodified production filters/controllers. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("disposable-acceptance")
@Testcontainers
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@EnabledIfSystemProperty(named = "pompom.acceptance", matches = "true")
@SuppressWarnings("removal") // Java 21 test-JVM network sandbox; never part of the shipped application.
class DisposableOwnerHttpAcceptanceTest {
  @Container static final PostgreSQLContainer<?> POSTGRES =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("disposable_owner_http")
          .withUsername("disposable_owner_http");
  static final ObjectMapper JSON = new ObjectMapper();
  static final String WORKSPACE_PARENT = "library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026";
  static final String WORKSPACE = WORKSPACE_PARENT + "/HTTP_ACCEPTANCE";
  static final String STORY = "Pip the rabbit wants to place a sticky note on a toy cabinet. "
      + "The note sticks to Pip's finger instead. Pip peels with the other hand and it splits into two notes, "
      + "one per hand. Each pull doubles the sticky notes from two to four to eight, covering Pip's arms and face. "
      + "Pip sees the note-covered reflection in a mirror and gasps. Pip remains covered until a sneeze scatters "
      + "the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.";
  static final String PROMPT = """
      TITLE / FORMAT
      Pip Sticky Notes / 15s Video
      VISUAL STYLE
      Bright playful animation.
      CHARACTER / CONTINUITY
      Pip is an anthropomorphic rabbit. Keep the same identity throughout.
      TIMED SHOT PLAN
      0-2s: Pip reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to Pip's finger [medium shot] -> the note sticks to Pip, not the cabinet
      2-5s: Pip tries to peel the stuck note away with the other hand; the note splits into two [medium shot] -> one note sticks to each hand
      5-10s: Pip continues to pull; each pull doubles the sticky notes from two to four to eight, covering Pip's arms and face [wide shot] -> Pip is overwhelmed by notes
      10-12s: Pip sees the note-covered reflection in a mirror and gasps; the notes remain attached through this reaction [close-up] -> Pip is startled
      12-15s: Pip sneezes and the sticky notes fly off onto the cabinet [medium shot] -> Pip is relieved, but the cabinet remains messy
      AUDIO
      Playful music; peel, gasp and sneeze effects.
      NEGATIVE CONSTRAINTS
      No violence, dialogue, identity changes or extra actions.
      FINAL CUT
      Pip relieved beside the messy cabinet.
      PRODUCTION SETTINGS
      9:16. ABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15s. image2video. 480p.
      """;
  static Path temporaryRoot;
  static Path credentialFile;
  static String credential;
  static URI ml;
  static boolean storyMode(){return Set.of("--story-evolution","--story-feasibility").contains(System.getProperty("pompom.acceptance.mode"));}
  static boolean storyFeasibilityMode(){return "--story-feasibility".equals(System.getProperty("pompom.acceptance.mode"));}
  static LoopbackOnly networkGuard;
  static SecurityManager previousSecurityManager;

  @BeforeAll static void prepareIsolatedRuntime() throws Exception {
    ml = URI.create(System.getProperty("pompom.acceptance.ml-url", ""));
    assertThat(ml.getScheme()).isEqualTo("http");
    assertThat(ml.getHost()).isEqualTo("127.0.0.1");
    assertThat(ml.getPort()).isPositive();
    assertThat(System.getenv("CPQ_PILOT_REAL_ENABLED")).isNotEqualTo("true");
    for (String key : List.of("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OPENART_API_KEY",
        "CPQ_OWNER_SECRET_FILE", "DB_URL", "DB_PASSWORD")) {
      assertThat(System.getenv(key)).as("Production configuration must be absent: %s", key).isNull();
    }
    temporaryRoot = Files.createTempDirectory("pompom-owner-http-");
    Files.setPosixFilePermissions(temporaryRoot, PosixFilePermissions.fromString("rwx------"));
    Files.createDirectories(temporaryRoot.resolve(WORKSPACE_PARENT));
    byte[] secretBytes = new byte[48];
    new SecureRandom().nextBytes(secretBytes);
    credential = Base64.getUrlEncoder().withoutPadding().encodeToString(secretBytes);
    credentialFile = temporaryRoot.resolve("owner.credential");
    Files.createFile(credentialFile, PosixFilePermissions.asFileAttribute(
        PosixFilePermissions.fromString("rw-------")));
    Files.writeString(credentialFile, credential);
    assertThat(POSTGRES.getJdbcUrl()).contains("/disposable_owner_http");
    assertThat(POSTGRES.getMappedPort(5432)).isNotEqualTo(5432);
    previousSecurityManager = System.getSecurityManager();
    networkGuard = new LoopbackOnly(Set.of(ml.getPort(), POSTGRES.getMappedPort(5432)));
    System.setSecurityManager(networkGuard);
  }

  @AfterAll static void cleanup() throws Exception {
    System.setSecurityManager(previousSecurityManager);
    credential = null;
    if (temporaryRoot != null) {
      try (var files = Files.walk(temporaryRoot)) {
        for (Path file : files.sorted(java.util.Comparator.reverseOrder()).toList()) {
          Files.deleteIfExists(file);
        }
      }
    }
  }

  @DynamicPropertySource static void properties(DynamicPropertyRegistry r) {
    r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
    r.add("spring.datasource.username", POSTGRES::getUsername);
    r.add("spring.datasource.password", POSTGRES::getPassword);
    r.add("ml.service.url", () -> ml.toString());
    r.add("pompom.ml-base-url", () -> ml.toString());
    r.add("pompom.qa.service.url", () -> ml.toString());
    r.add("server.address", () -> "127.0.0.1");
    r.add("pompom.cpq-owner.id", () -> "disposable-owner");
    r.add("pompom.cpq-owner.secret-file", () -> credentialFile.toString());
    r.add("pompom.cpq-pilot.real-enabled", () -> storyMode()?"true":"false");
    r.add("pompom.story-evolution.poll-delay-ms", () -> "150");
    r.add("pompom.data-root", () -> temporaryRoot.toString());
    r.add("management.health.mail.enabled", () -> "false");
    r.add("pompom.openart.enabled", () -> "false");
    r.add("spring.ai.enabled", () -> "false");
  }

  @LocalServerPort int port;
  @Value("${spring.datasource.url}") String jdbcUrl;
  @Autowired JdbcTemplate jdbc;
  @Autowired ScheduledAnnotationBeanPostProcessor scheduledTasks;
  final List<Map<String,Object>> trace = new ArrayList<>();
  HttpClient client;
  String base;
  String csrf;

  @Test void authenticatedOwnerCreatesAndReadsApprovedSourceOverActualHttp() throws Exception {
    // Stop only this disposable application's background workers; HTTP and all security remain real.
    if(!storyMode())scheduledTasks.getScheduledTasks().forEach(task -> task.cancel(false));
    networkGuard.ports.add(port);
    base = "http://127.0.0.1:" + port;
    CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
    client = HttpClient.newBuilder().cookieHandler(cookies).connectTimeout(Duration.ofSeconds(5))
        .version(HttpClient.Version.HTTP_1_1).build();
    assertThat(jdbcUrl).isEqualTo(POSTGRES.getJdbcUrl());
    assertThat(jdbc.queryForObject("SELECT current_database()", String.class)).isEqualTo("disposable_owner_http");
    String flyway = jdbc.queryForObject("SELECT version FROM flyway_schema_history WHERE success=true ORDER BY installed_rank DESC LIMIT 1", String.class);
    assertThat(flyway).isEqualTo("70");
    assertThat(jdbc.queryForObject("SELECT count(*) FROM flyway_schema_history WHERE version='69' AND success=true",Long.class)).isEqualTo(1);
    long migrations = jdbc.queryForObject("SELECT count(*) FROM flyway_schema_history WHERE success=true", Long.class);
    assertThat(migrations).isEqualTo(68);

    JsonNode health = call("GET", "/actuator/health", null, null, null, 200);
    assertThat(health.path("status").asText()).isEqualTo("UP");
    String ownerPath = "/api/v1/intelligence/workflow/owner-auth";
    String protectedRead = "/api/v1/intelligence/workflow/cpq/optimization-runs/latest?analysisId=" + UUID.randomUUID();
    call("GET", protectedRead, null, null, null, 403);
    JsonNode state = call("GET", ownerPath, null, null, null, 200);
    assertThat(state.path("configured").asBoolean()).isTrue();
    assertThat(state.path("authenticated").asBoolean()).isFalse();
    csrf = state.path("csrfToken").asText();
    call("POST", ownerPath + "/login", Map.of("credential", "wrong"), csrf, base, 401);
    call("POST", ownerPath + "/login", Map.of("credential", credential), null, base, 403);
    call("POST", ownerPath + "/login", Map.of("credential", credential), csrf, "https://attacker.invalid", 403);
    String anonymousSessionId = cookies.getCookieStore().getCookies().stream()
        .filter(c -> c.getName().equals("JSESSIONID")).findFirst().orElseThrow().getValue();
    // Do not record a response body, cookie value or credential in the evidence trace.
    JsonNode login = call("POST", ownerPath + "/login", Map.of("credential", credential), csrf, base, 200);
    assertThat(login.path("authenticated").asBoolean()).isTrue();
    assertThat(login.path("ownerId").asText()).isEqualTo("disposable-owner");
    assertThat(login.path("independentHumanReviewer").asBoolean()).isFalse();
    assertThat(cookies.getCookieStore().getCookies()).anyMatch(c -> c.getName().equals("JSESSIONID") && c.isHttpOnly());
    assertThat(cookies.getCookieStore().getCookies().stream().filter(c -> c.getName().equals("JSESSIONID"))
        .findFirst().orElseThrow().getValue()).isNotEqualTo(anonymousSessionId);
    String anonymousCsrf = csrf;
    csrf = login.path("csrfToken").asText();
    assertThat(csrf).isNotEqualTo(anonymousCsrf);
    call("GET", protectedRead, null, null, null, 200);
    call("GET", "/api/v1/intelligence/workflow/cpq/original-prompts/" + UUID.randomUUID()
        + "/fidelity-review", null, null, null, 403);

    String policyPath = "/api/v1/intelligence/workflow/cpq/original-prompts/preflight";
    call("POST", policyPath, Map.of(), null, base, 403);
    call("POST", policyPath, Map.of(), csrf, "https://attacker.invalid", 403);

    // Workspace is created by the existing workspace API under the isolated data root.
    call("POST", "/api/v1/videos/prompt-workspaces/folders",
        Map.of("parentDirectory", WORKSPACE_PARENT, "folderName", "HTTP_ACCEPTANCE"), csrf, base, 200);
    JsonNode content = post("/api/v1/intelligence/contents", Map.of(
        "title", "Disposable Pip story", "description", "P0 isolated HTTP source", "type", "SHORT"), 200);
    long contentId = content.path("id").asLong();
    assertThat(contentId).isPositive();

    JsonNode story = post("/api/v1/intelligence/workflow/creative-role", Map.of(
        "role", "STORY", "text", STORY, "generationAuthorized", true, "maxCostUsd", 0.01,
        "context", Map.of("workspacePath", WORKSPACE, "inputMode", "DETAILED_STORY",
            "requestedAlternativeCount", 2, "storyGenerationMode", "IMPROVE_EXISTING_STORY")), 200);
    assertThat(story.path("provider").asText()).isEqualTo("ISOLATED_FIXTURE");
    assertThat(story.path("providerDispatched").asBoolean(true)).isFalse();
    assertThat(story.path("calls").asInt(-1)).isZero();
    String generatedId = story.path("recordId").asText();
    JsonNode initial = story.path("result").path("alternatives").get(0);
    assertThat(initial).isNotNull();
    String initialText = initial.path("text").asText();
    String candidate = initial.path("candidateId").asText();
    // Persist a source revision through the existing revision validation, never by SQL insertion.
    JsonNode revision = post("/api/v1/intelligence/workflow/records/" + generatedId + "/story-revisions",
        Map.of("candidateId", candidate, "revisionId", candidate + "-revision-" + revisionFingerprint(initialText),
            "text", STORY, "title", "Pip acceptance source revision"), 200);
    String storyId = revision.path("recordId").asText();
    String revisionId = revision.path("result").path("revisionId").asText();
    candidate = revision.path("result").path("alternatives").get(0).path("candidateId").asText();
    assertThat(storyId).isNotBlank();
    assertThat(revisionId).isEqualTo(candidate + "-revision-" + revisionFingerprint(STORY));
    Map<String,Object> approval = Map.of("approvedText", STORY, "candidateId", candidate,
        "revisionId", revisionId, "contentFingerprint", revisionFingerprint(STORY),
        "sourceType", "DISPOSABLE_HTTP_ACCEPTANCE");
    Map<String,Object> stale = new LinkedHashMap<>(approval);
    stale.put("contentFingerprint", "invalid");
    post("/api/v1/intelligence/workflow/creative-role/" + storyId + "/approve-story", stale, 409);
    JsonNode approved = post("/api/v1/intelligence/workflow/creative-role/" + storyId + "/approve-story", approval, 200);
    String approvalId = approved.path("recordId").asText();
    assertThat(approvalId).isNotBlank();

    JsonNode prompt = post("/api/v1/intelligence/contents/" + contentId + "/prompt-versions",
        Map.of("rawText", PROMPT), 201);
    long promptId = prompt.path("id").asLong();
    assertThat(promptId).isPositive();
    JsonNode studio = post("/api/v1/intelligence/workflow/studio-sessions", Map.of(
        "contentId", contentId, "promptVersionId", promptId, "sourceStoryRecordId", storyId,
        "storyRevisionId", revisionId, "approvalRecordId", approvalId, "candidateId", candidate,
        "approvedStoryText", STORY, "workspacePath", WORKSPACE), 200);
    JsonNode production = post("/api/v1/intelligence/workflow/production-settings", Map.of(
        "contentId", contentId, "promptVersionId", promptId, "contentProfile", "ABSURD_PHYSICS",
        "generator", "SEEDANCE_2_0_MINI", "desiredDuration", 15, "openingStrategy", "AUTO",
        "settings", Map.of("mode", "image2video", "resolution", "480p", "aspectRatio", "9:16")), 200);
    // A valid session + CSRF reaches the existing permission and source policy evaluator.
    JsonNode policy = post(policyPath, Map.of("contentId", contentId, "promptVersionId", promptId,
        "expectedPromptSha256", sha256(PROMPT)), 200);
    assertThat(policy.path("persisted").asBoolean(true)).isFalse();
    assertThat(policy.path("state").asText(policy.path("status").asText())).isEqualTo("READY_FOR_SOURCE_BINDING");
    assertThat(policy.path("blockers")).isEmpty();

    JsonNode analysis = post("/api/v1/intelligence/workflow/review", Map.of(
        "contentId", contentId, "promptVersionId", promptId,
        "options", Map.of("profile", "post-family-v1", "canonicalRulesetVersion", "1.11",
            "contentProfile", "ABSURD_PHYSICS", "generator", "SEEDANCE_2_0_MINI", "desiredDuration", 15,
            "settings", Map.of("mode", "image2video", "resolution", "480p", "aspectRatio", "9:16"))), 200);
    String analysisId = analysis.path("recordId").asText();
    JsonNode canonical = analysis.path("canonicalRuleEvaluation");
    assertThat(analysisId).isNotBlank();
    assertThat(canonical.path("status").asText()).isEqualTo("EVALUATED");
    assertThat(canonical.path("rulesetVersion").asText()).isEqualTo("1.11");
    assertThat(canonical.path("score").isNumber()).isTrue();

    JsonNode readback = call("GET", "/api/v1/intelligence/workflow/records/" + approvalId, null, null, null, 200);
    assertThat(readback.path("storyRecordId").asText()).isEqualTo(storyId);
    assertThat(readback.path("approvedText").asText()).isEqualTo(STORY);
    assertThat(readback.path("revisionId").asText()).isEqualTo(revisionId);
    assertThat(sha256(readback.path("approvedText").asText())).isEqualTo(sha256(STORY));
    JsonNode storyReadback = call("GET", "/api/v1/intelligence/workflow/records/" + storyId, null, null, null, 200);
    assertThat(storyReadback.path("result").path("alternatives").get(0).path("text").asText()).isEqualTo(STORY);
    JsonNode prompts = call("GET", "/api/v1/intelligence/contents/" + contentId + "/prompt-versions", null, null, null, 200);
    assertThat(prompts.get(0).path("rawText").asText()).isEqualTo(PROMPT);
    JsonNode savedAnalysis = call("GET", "/api/v1/intelligence/workflow/records/" + analysisId, null, null, null, 200);
    assertThat(savedAnalysis.path("canonicalRuleEvaluation")).isEqualTo(canonical);
    assertThat(savedAnalysis.path("boundRequest").path("prompt").asText()).isEqualTo(PROMPT);
    assertThat(savedAnalysis.path("contentId").asLong()).isEqualTo(contentId);
    assertThat(savedAnalysis.path("promptVersionId").asLong()).isEqualTo(promptId);
    JsonNode boundSource = call("GET", "/api/v1/intelligence/workflow/cpq/story-evolution-source?analysisId="
        + analysisId, null, null, null, 200);
    assertThat(boundSource.path("storyRecordId").asText()).isEqualTo(storyId);
    assertThat(boundSource.path("approvalRecordId").asText()).isEqualTo(approvalId);
    assertThat(boundSource.path("story").asText()).isEqualTo(STORY);
    assertThat(boundSource.path("storySha256").asText()).isEqualTo(sha256(STORY));

    JsonNode evolution = "--story-evolution".equals(System.getProperty("pompom.acceptance.mode")) ? evolveStory(contentId,promptId,storyId,approvalId,analysis,canonical) : null;
    JsonNode feasibility = storyFeasibilityMode() ? evolveStoryFeasibility(contentId,promptId,storyId,approvalId,analysis,canonical) : null;
    if(storyMode())scheduledTasks.getScheduledTasks().forEach(task -> task.cancel(false));
    call("POST", ownerPath + "/logout", Map.of(), null, base, 403);
    call("POST", ownerPath + "/logout", Map.of(), csrf, base, 200);
    call("GET", protectedRead, null, null, null, 403);
    assertThat(call("GET", ownerPath, null, null, null, 200).path("authenticated").asBoolean()).isFalse();
    // Exercise the real HTTP rate limiter with a fresh, disposable unauthenticated session.
    csrf = call("GET", ownerPath, null, null, null, 200).path("csrfToken").asText();
    for (int i = 0; i < 5; i++) call("POST", ownerPath + "/login", Map.of("credential", "wrong"), csrf, base, 401);
    call("POST", ownerPath + "/login", Map.of("credential", credential), csrf, base, 401);

    networkGuard.probe.set(true);
    try {
      assertThatThrownBy(() -> new java.net.Socket("198.51.100.1", 443)).isInstanceOf(SecurityException.class);
      assertThatThrownBy(() -> new java.net.Socket("127.0.0.1", 5432)).isInstanceOf(SecurityException.class);
    } finally { networkGuard.probe.remove(); }
    assertThat(networkGuard.unexpectedAttempts).isEmpty();
    Map<String,Object> evidence = new LinkedHashMap<>();
    evidence.put("p0HttpAcceptance", true);
    if(evolution!=null)evidence.put("storyEvolution",evolution);
    if(feasibility!=null)evidence.put("storyFeasibility",feasibility);
    evidence.put("backendPort", port); evidence.put("backendBaseUrl", base);
    evidence.put("postgresContainerId", POSTGRES.getContainerId());
    evidence.put("postgresJdbcUrl", POSTGRES.getJdbcUrl());
    evidence.put("postgresDatabase", "disposable_owner_http");
    evidence.put("flywayVersion", flyway); evidence.put("flywayMigrationCount", migrations);
    evidence.put("mlBaseUrl", ml.toString()); evidence.put("mlFixtureConnected", true);
    evidence.put("ownerLoginHttp", true); evidence.put("ownerSession", true);
    evidence.put("csrfAndOriginVerified", true); evidence.put("logoutRevocationVerified", true);
    evidence.put("rateLimitingVerified", true); evidence.put("sessionCookieReturned", true);
    evidence.put("contentId", contentId); evidence.put("generatedStoryId", generatedId);
    evidence.put("approvedStoryId", storyId); evidence.put("storyRevisionId", revisionId);
    evidence.put("storyApprovalId", approvalId); evidence.put("approvedStorySha256", sha256(STORY));
    evidence.put("storyRevisionFingerprint", revisionFingerprint(STORY));
    evidence.put("promptVersionId", promptId); evidence.put("promptSha256", sha256(PROMPT));
    evidence.put("analysisId", analysisId); evidence.put("canonical", canonical);
    evidence.put("studioSessionRecordId", studio.path("recordId").asText());
    evidence.put("productionSettingsRecordId", production.path("recordId").asText());
    evidence.put("sourceReadbackHttp", true);
    evidence.put("nextOperation", "STORY_EVOLUTION_HTTP_START");
    evidence.put("promptProvenanceScope", "OPERATOR_SAVED_TEST_PROMPT; NOT_BUILD_PROMPT_OR_OPTIMIZER_OUTPUT");
    evidence.put("networkPolicy", "JVM_EXACT_LOOPBACK_PORT_ALLOWLIST_AND_ML_SOCKET_DENY_EGRESS");
    evidence.put("networkNegativeProbes", List.of("external:443 denied", "production-loopback:5432 denied"));
    evidence.put("unexpectedNetworkAttempts", networkGuard.unexpectedAttempts);
    evidence.put("productionDatabaseWrites", 0); evidence.put("realProviderCalls", 0);
    evidence.put("realImageCalls", 0); evidence.put("realRenderCalls", 0);
    evidence.put("httpTrace", trace);
    Path output = Path.of(System.getProperty("pompom.acceptance.output"));
    Files.createDirectories(output.toAbsolutePath().getParent());
    Files.writeString(output, JSON.writerWithDefaultPrettyPrinter().writeValueAsString(evidence));
  }

  JsonNode evolveStory(long content,long parentPrompt,String source,String sourceApproval,JsonNode baseline,JsonNode baselineCanonical) throws Exception {
    assertThat(System.getenv("WORKFLOW_ADAPTIVE_DISPATCH_TOKEN")).hasSizeGreaterThanOrEqualTo(32);
    String startPath="/api/v1/intelligence/workflow/cpq/story-evolution-runs";
    var grant=new LinkedHashMap<String,Object>();
    grant.put("sourceStoryRecordId",source);grant.put("approvalRecordId",sourceApproval);
    grant.put("idempotencyKey",UUID.randomUUID().toString());grant.put("objective","Clarify visible causal contact, progression states and mirror continuity; preserve events, rule and ending");
    grant.put("maxRounds",2);grant.put("maxRequests",4);grant.put("maxTotalUsd",0.08);grant.put("maxRunSeconds",60);
    grant.put("authorizePaidInference",true);grant.put("confirmSourceAuthority",true);grant.put("automaticRetries",false);
    JsonNode started=post(startPath,grant,200);String runId=started.path("runId").asText();
    assertThat(runId).isNotBlank();
    assertThat(post(startPath,grant,200).path("runId").asText()).isEqualTo(runId);
    final var completed=new java.util.concurrent.atomic.AtomicReference<JsonNode>();
    org.awaitility.Awaitility.await().atMost(Duration.ofSeconds(40)).pollInterval(Duration.ofMillis(150)).until(() -> {
      JsonNode current=call("GET",startPath+"/"+runId,null,null,null,200);completed.set(current);
      return !Set.of("READY","RUNNING").contains(current.path("state").asText());
    });
    JsonNode run=completed.get();
    assertThat(run.path("state").asText()).as("Actual worker result: %s",run).isEqualTo("AWAITING_OWNER_STORY_APPROVAL");
    assertThat(run.path("drafts")).hasSize(2);
    assertThat(run.path("progress").path("round").asInt()).isEqualTo(2);
    assertThat(run.path("progress").path("requestCount").asInt()).isEqualTo(4);
    assertThat(run.path("progress").path("providerCalls").asInt()).isZero();
    assertThat(run.path("progress").path("actualCostUsd").asDouble()).isZero();
    assertThat(run.path("progress").path("rejectedCandidates").toString()).contains("round-2-equivalent","EQUIVALENT_OR_MEANINGLESS");
    JsonNode first=run.path("drafts").get(0),second=run.path("drafts").get(1);
    for(JsonNode d:run.path("drafts"))assertThat(sha256(d.path("payload").path("text").asText())).isEqualTo(d.path("candidateSha256").asText());
    String best=run.path("progress").path("bestDraftId").asText();
    assertThat(best).isEqualTo(second.path("draftId").asText());
    assertThat(second.path("payload").path("parentDraftId").asText()).isEqualTo(first.path("draftId").asText());
    assertThat(run.path("events").toString()).contains("ROUND_RETAINED","AWAITING_OWNER_STORY_APPROVAL","REQUEST_RESERVED","REQUEST_COMPLETED");
    // A stale hash and a non-best draft must not be promoted.
    post(startPath+"/"+runId+"/approve",Map.of("draftId",best,"candidateSha256","stale"),409);
    post(startPath+"/"+runId+"/approve",Map.of("draftId",first.path("draftId").asText(),"candidateSha256",first.path("candidateSha256").asText()),409);
    JsonNode approved=post(startPath+"/"+runId+"/approve",Map.of("draftId",best,"candidateSha256",second.path("candidateSha256").asText()),200);
    assertThat(approved.path("state").asText()).isEqualTo("APPROVED_NEW_SOURCE");
    JsonNode approval=approved.path("progress").path("approval");String newStory=approval.path("storyRecordId").asText();
    assertThat(newStory).isNotBlank().isNotEqualTo(source);
    JsonNode newApproved=call("GET","/api/v1/intelligence/workflow/records/"+approval.path("recordId").asText(),null,null,null,200);
    assertThat(sha256(newApproved.path("approvedText").asText())).isEqualTo(second.path("candidateSha256").asText());
    JsonNode old=call("GET","/api/v1/intelligence/workflow/records/"+sourceApproval,null,null,null,200);
    assertThat(old.path("approvedText").asText()).isEqualTo(STORY);
    JsonNode handed=post(startPath+"/"+runId+"/prompt-handoff",Map.of(
      "contentId",content,"parentPromptVersionId",parentPrompt,"authorizePromptGeneration",true,"automaticRetries",false,
      "maxCostUsd",0.04,"desiredDuration",15,"mainCharacter","Pip","contentProfile","ABSURD_PHYSICS",
      "generator","SEEDANCE_2_0_MINI","settings",Map.of("aspectRatio","9:16","mode","image2video","resolution","480p")),200);
    assertThat(handed.path("state").asText()).isEqualTo("PROMPT_HANDOFF_COMPLETE");
    JsonNode handoff=handed.path("progress").path("promptHandoff");long prompt=handoff.path("newPromptId").asLong();
    String analysisId=handoff.path("analysisId").asText();long validationId=handoff.path("qualityValidationId").asLong();
    assertThat(prompt).isPositive().isNotEqualTo(parentPrompt);assertThat(analysisId).isNotBlank();assertThat(validationId).isPositive();
    JsonNode prompts=call("GET","/api/v1/intelligence/contents/"+content+"/prompt-versions",null,null,null,200);
    JsonNode savedPrompt=prompts.get(0);String text=savedPrompt.path("rawText").asText();
    assertThat(savedPrompt.path("id").asLong()).isEqualTo(prompt);
    assertThat(savedPrompt.path("versionNumber").asInt()).isEqualTo(2);
    assertThat(sha256(text)).isEqualTo(handoff.path("promptFingerprint").asText());
    JsonNode analysis=call("GET","/api/v1/intelligence/workflow/records/"+analysisId,null,null,null,200);
    JsonNode canonical=analysis.path("canonicalRuleEvaluation");
    assertThat(handoff.path("canonicalEvaluation")).isEqualTo(canonical);
    assertThat(canonical.path("status").asText()).isEqualTo("EVALUATED");
    assertThat(canonical.path("rulesetVersion").asText()).isEqualTo("1.11");assertThat(canonical.path("score").isNumber()).isTrue();
    assertThat(analysis.path("boundRequest").path("prompt").asText()).isEqualTo(text);
    JsonNode newSource=call("GET","/api/v1/intelligence/workflow/cpq/story-evolution-source?analysisId="+analysisId,null,null,null,200);
    assertThat(newSource.path("storyRecordId").asText()).isEqualTo(newStory);
    assertThat(newSource.path("storySha256").asText()).isEqualTo(second.path("candidateSha256").asText());
    // Read-only persistence verification; all writes above went through HTTP business operations.
    assertThat(jdbc.queryForObject("SELECT prompt_version_id FROM quality_validations WHERE id=?",Long.class,validationId)).isEqualTo(prompt);
    String persistedVersion=jdbc.queryForObject("SELECT ruleset_version FROM quality_validations WHERE id=?",String.class,validationId);
    assertThat(persistedVersion).startsWith("1.11+profile-admission-v1:").hasSizeGreaterThan(10);
    JsonNode validationReport=JSON.readTree(jdbc.queryForObject("SELECT report_json FROM quality_validations WHERE id=?",String.class,validationId));
    assertThat(validationReport.path("rulesetVersion").asText()).isEqualTo(persistedVersion);
    assertThat(jdbc.queryForObject("SELECT count(*) FROM quality_validation_stats WHERE ruleset_version=?",Long.class,persistedVersion)).isEqualTo(1);
    JsonNode preflight=call("GET","/api/v1/intelligence/workflow/records/"+analysisId+"/creative-optimization/preflight",null,null,null,200);
    assertThat(preflight.path("sourcePromptVersionId").asLong()).isEqualTo(prompt);
    // This story retains two attempts and unknown visual evidence. The actual policy, not the fixture, decides.
    assertThat(preflight.path("generationAllowed").asBoolean()).as("Eligible continuation must be executed, not silently skipped: %s",preflight).isFalse();
    var providerRequests=new ArrayList<JsonNode>();
    for(String line:Files.readAllLines(Path.of(System.getProperty("pompom.acceptance.provider-trace"))))providerRequests.add(JSON.readTree(line));
    JsonNode round2=providerRequests.stream().filter(x -> x.path("role").asText().equals("STORY") && x.path("request").path("context").path("roundNumber").asInt()==2).findFirst().orElseThrow();
    JsonNode actualContext=round2.path("request").path("context");
    assertThat(actualContext.path("bestCandidate").path("text").asText()).isEqualTo(first.path("payload").path("text").asText());
    assertThat(actualContext.path("previousAssessment").path("reviewId").asText()).isEqualTo(first.path("payload").path("review").path("reviewId").asText());
    assertThat(actualContext.path("previousRevision").asText()).isEqualTo(first.path("draftId").asText());
    var out=JSON.createObjectNode();out.put("p1Acceptance",true);out.put("evolutionRunId",runId);out.set("completedRun",run);
    out.set("approvedRun",approved);out.set("handoffRun",handed);out.set("newSource",newSource);out.set("savedPrompt",savedPrompt);
    out.set("newAnalysis",analysis);out.set("canonical",canonical);out.set("preflight",preflight);out.set("baselineCanonical",baselineCanonical);
    out.put("roundsExecuted",2);out.put("requestCount",4);out.put("providerCalls",0);out.put("actualCostUsd",0);out.put("hmacVerified",true);
    out.put("newPromptId",prompt);out.put("analysisId",analysisId);out.put("qualityValidationId",validationId);out.put("qualityValidationRulesetVersion",persistedVersion);out.set("persistedQualityReport",validationReport);
    out.put("optimizationRounds",0);out.put("optimizationStopReason",preflight.path("state").asText());
    return out;
  }

  JsonNode evolveStoryFeasibility(long content,long parentPrompt,String source,String sourceApproval,JsonNode baseline,JsonNode baselineCanonical) throws Exception {
    String path="/api/v1/intelligence/workflow/cpq/story-evolution-runs";
    String baselineAnalysisId=baseline.path("recordId").asText();
    assertThat(baselineAnalysisId).isNotBlank();

    var negativeGrant=new LinkedHashMap<String,Object>();
    negativeGrant.put("sourceStoryRecordId",source);negativeGrant.put("approvalRecordId",sourceApproval);
    negativeGrant.put("baselineAnalysisId",baselineAnalysisId);negativeGrant.put("idempotencyKey",UUID.randomUUID().toString());
    negativeGrant.put("objective","P2_NEGATIVE_STRUCTURAL_CASE");negativeGrant.put("maxRounds",1);negativeGrant.put("maxRequests",2);
    negativeGrant.put("maxTotalUsd",0.02);negativeGrant.put("maxRunSeconds",60);negativeGrant.put("authorizePaidInference",true);
    negativeGrant.put("confirmSourceAuthority",true);negativeGrant.put("automaticRetries",false);
    JsonNode negativeStarted=post(path,negativeGrant,200);String negativeId=negativeStarted.path("runId").asText();
    final var negativeDone=new java.util.concurrent.atomic.AtomicReference<JsonNode>();
    org.awaitility.Awaitility.await().atMost(Duration.ofSeconds(30)).pollInterval(Duration.ofMillis(150)).until(()->{
      JsonNode current=call("GET",path+"/"+negativeId,null,null,null,200);negativeDone.set(current);
      return !Set.of("READY","RUNNING").contains(current.path("state").asText());
    });
    JsonNode negative=negativeDone.get();
    assertThat(negative.path("state").asText()).isEqualTo("STOPPED");
    assertThat(negative.path("progress").path("reason").asText()).isEqualTo("NO_ELIGIBLE_STORY_CANDIDATE");
    assertThat(negative.path("drafts")).isEmpty();
    assertThat(negative.path("progress").path("reviewedCandidates")).hasSize(2);
    assertThat(negative.path("progress").path("lastAssessment").path("structuralFeasibilityAssessment").toString()).contains("STRUCTURALLY_BLOCKED","NOT_SUPPORTED");

    var grant=new LinkedHashMap<String,Object>();
    grant.put("sourceStoryRecordId",source);grant.put("approvalRecordId",sourceApproval);grant.put("baselineAnalysisId",baselineAnalysisId);
    grant.put("idempotencyKey",UUID.randomUUID().toString());grant.put("objective","P2_POSITIVE_STRUCTURAL_CASE");
    grant.put("maxRounds",2);grant.put("maxRequests",4);grant.put("maxTotalUsd",0.08);grant.put("maxRunSeconds",60);
    grant.put("authorizePaidInference",true);grant.put("confirmSourceAuthority",true);grant.put("automaticRetries",false);
    JsonNode started=post(path,grant,200);String runId=started.path("runId").asText();
    final var positiveDone=new java.util.concurrent.atomic.AtomicReference<JsonNode>();
    org.awaitility.Awaitility.await().atMost(Duration.ofSeconds(40)).pollInterval(Duration.ofMillis(150)).until(()->{
      JsonNode current=call("GET",path+"/"+runId,null,null,null,200);positiveDone.set(current);
      return !Set.of("READY","RUNNING").contains(current.path("state").asText());
    });
    JsonNode run=positiveDone.get();
    assertThat(run.path("state").asText()).as("P2 positive run: %s",run).isEqualTo("AWAITING_OWNER_STORY_APPROVAL");
    assertThat(run.path("drafts")).hasSize(2);assertThat(run.path("progress").path("round").asInt()).isEqualTo(2);
    assertThat(run.path("progress").path("requestCount").asInt()).isEqualTo(4);
    assertThat(run.path("progress").path("providerCalls").asInt()).isZero();
    JsonNode second=run.path("drafts").get(1);String best=run.path("progress").path("bestDraftId").asText();
    assertThat(best).isEqualTo(second.path("draftId").asText());
    assertThat(second.path("payload").path("review").path("creativeQualityAssessment").toString()).contains("CREATIVELY_STRONG");
    assertThat(second.path("payload").path("review").path("structuralFeasibilityAssessment").toString()).contains("STRUCTURALLY_PROMISING","ATTEMPT_001","MINI_STORY_LOCK");
    post(path+"/"+runId+"/approve",Map.of("draftId",best,"candidateSha256","stale"),409);
    JsonNode approved=post(path+"/"+runId+"/approve",Map.of("draftId",best,"candidateSha256",second.path("candidateSha256").asText()),200);
    assertThat(approved.path("state").asText()).isEqualTo("APPROVED_NEW_SOURCE");
    String newStory=approved.path("progress").path("approval").path("storyRecordId").asText();
    JsonNode handed=post(path+"/"+runId+"/prompt-handoff",Map.of(
      "contentId",content,"parentPromptVersionId",parentPrompt,"authorizePromptGeneration",true,"automaticRetries",false,
      "maxCostUsd",0.04,"desiredDuration",15,"mainCharacter","Pip","contentProfile","ABSURD_PHYSICS",
      "generator","SEEDANCE_2_0_MINI","settings",Map.of("aspectRatio","9:16","mode","image2video","resolution","480p")),200);
    assertThat(handed.path("state").asText()).isEqualTo("PROMPT_HANDOFF_COMPLETE");
    JsonNode handoff=handed.path("progress").path("promptHandoff");long prompt=handoff.path("newPromptId").asLong();
    String analysisId=handoff.path("analysisId").asText();
    JsonNode saved=call("GET","/api/v1/intelligence/workflow/records/"+analysisId,null,null,null,200);
    JsonNode canonical=saved.path("canonicalRuleEvaluation");
    assertThat(canonical.path("status").asText()).isEqualTo("EVALUATED");assertThat(canonical.path("rulesetVersion").asText()).isEqualTo("1.11");
    assertThat(canonical.path("score").isNumber()).isTrue();assertThat(canonical.path("grade").asText()).isNotBlank();
    assertThat(saved.path("boundRequest").path("prompt").asText()).contains("tries to place","Pip tries to peel","Pip tries to press","Pip tries to push");
    JsonNode preflight=call("GET","/api/v1/intelligence/workflow/records/"+analysisId+"/creative-optimization/preflight",null,null,null,200);
    assertThat(preflight.path("sourceAnalysisId").asText()).isEqualTo(analysisId);
    assertThat(preflight.path("generationAllowed").asBoolean()).isFalse();
    assertThat(preflight.path("researchGenerationEligibility").path("allowed").asBoolean()).isTrue();
    assertThat(preflight.path("researchGenerationEligibility").path("finalCanonicalAAdmitted").asBoolean()).isFalse();
    assertThat(preflight.path("researchGenerationEligibility").path("imageGenerationAllowed").asBoolean()).isFalse();
    assertThat(preflight.path("researchGenerationEligibility").path("renderAuthorized").asBoolean()).isFalse();
    JsonNode researchPreflight=post("/api/v1/intelligence/workflow/cpq/optimization-runs/preflight",Map.of("analysisId",analysisId),200);
    JsonNode comparisonPlan=researchPreflight.path("researchComparisonPlan");
    assertThat(comparisonPlan.path("runs")).hasSize(2);
    assertThat(comparisonPlan.path("maximumRequests").asInt()).isEqualTo(6);
    assertThat(comparisonPlan.path("providerCalls").asInt()).isZero();
    assertThat(comparisonPlan.path("promptApprovalAllowed").asBoolean()).isFalse();
    assertThat(comparisonPlan.path("imageGenerationAllowed").asBoolean()).isFalse();
    assertThat(comparisonPlan.path("renderAuthorized").asBoolean()).isFalse();
    post("/api/v1/intelligence/workflow/cpq/optimization-runs",Map.of("analysisId",analysisId,"researchOnly",true),400);
    JsonNode old=call("GET","/api/v1/intelligence/workflow/records/"+sourceApproval,null,null,null,200);
    assertThat(old.path("approvedText").asText()).isEqualTo(STORY);

    var providerRequests=new ArrayList<JsonNode>();
    for(String line:Files.readAllLines(Path.of(System.getProperty("pompom.acceptance.provider-trace"))))providerRequests.add(JSON.readTree(line));
    var p2Requests=providerRequests.stream().filter(x->x.path("request").path("context").path("objective").asText().startsWith("P2_")).toList();
    assertThat(p2Requests).hasSize(6);
    var contexts=p2Requests.stream().filter(x->Set.of("STORY","STORY_REVIEW").contains(x.path("role").asText()))
      .map(x->x.path("request").path("context").path("canonicalStoryFeasibilityContext")).toList();
    assertThat(contexts).hasSize(6).allMatch(x->x.path("version").asText().equals("canonical-story-feasibility-context-v1")
      && x.path("rulesetVersion").asText().equals("1.11") && x.path("baselineAnalysisId").asText().equals(baselineAnalysisId)
      && x.path("contextSha256").asText().length()==64);
    assertThat(contexts.stream().map(x->x.path("contextSha256").asText()).distinct().count()).isEqualTo(1);

    var positive=JSON.createObjectNode();positive.put("runId",runId);positive.set("completedRun",run);positive.set("approvedRun",approved);
    positive.set("handoffRun",handed);positive.set("canonical",canonical);positive.set("preflight",preflight);positive.set("researchPreflight",researchPreflight);
    positive.put("roundsExecuted",2);positive.put("requestCount",4);positive.put("providerCalls",0);positive.put("actualCostUsd",0);
    positive.put("newPromptId",prompt);positive.put("analysisId",analysisId);positive.put("newStoryRecordId",newStory);
    positive.put("structuralPrediction","STRUCTURALLY_PROMISING");positive.put("actualCanonicalScore",canonical.path("score").asDouble());
    positive.put("actualCanonicalGrade",canonical.path("grade").asText());positive.put("generationAllowed",preflight.path("generationAllowed").asBoolean());
    var out=JSON.createObjectNode();out.put("p2Acceptance",true);out.set("negativeCase",negative);out.set("positiveCase",positive);
    out.set("baselineCanonical",baselineCanonical);out.put("predictionIsCanonicalPass",false);out.put("renderAuthorized",false);
    return out;
  }

  JsonNode post(String path, Object body, int expected) throws Exception {
    return call("POST", path, body, csrf, base, expected);
  }

  JsonNode call(String method, String path, Object body, String token, String origin, int expected) throws Exception {
    var request = HttpRequest.newBuilder(URI.create(base + path)).timeout(Duration.ofSeconds(40));
    if (token != null) request.header("X-CPQ-CSRF", token);
    if (origin != null) request.header("Origin", origin);
    if (body == null) request.GET();
    else request.header("Content-Type", "application/json")
        .method(method, HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)));
    var response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    trace.add(Map.of("method", method, "path", path, "status", response.statusCode(),
        "expectedStatus", expected, "csrfSupplied", token != null));
    assertThat(response.statusCode()).as("%s %s response: %s", method, path,
        path.endsWith("/login") ? "[authentication response omitted]" : response.body()).isEqualTo(expected);
    return response.body().isBlank() ? JSON.createObjectNode() : JSON.readTree(response.body());
  }

  static String sha256(String text) throws Exception {
    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
  }

  // Existing story API uses its documented FNV revision identifier; SHA-256 is separately verified.
  static String revisionFingerprint(String text) {
    int hash = 0x811c9dc5;
    for (int i = 0; i < text.length(); i++) { hash ^= text.charAt(i); hash *= 0x01000193; }
    return String.format(java.util.Locale.ROOT, "%08x", hash);
  }

  /** Test-only Java 21 sandbox denies provider hosts and all non-allowlisted local service ports. */
  static final class LoopbackOnly extends SecurityManager {
    final Set<Integer> ports = ConcurrentHashMap.newKeySet();
    final List<String> unexpectedAttempts = java.util.Collections.synchronizedList(new ArrayList<>());
    final ThreadLocal<Boolean> probe = ThreadLocal.withInitial(() -> false);
    LoopbackOnly(Set<Integer> allowed) { ports.addAll(allowed); }
    @Override public void checkPermission(Permission permission) { }
    @Override public void checkPermission(Permission permission, Object context) { }
    @Override public void checkConnect(String host, int port) {
      boolean loopback = Set.of("localhost", "127.0.0.1", "::1", "[::1]", "0:0:0:0:0:0:0:1").contains(host);
      if (loopback && (port == -1 || ports.contains(port))) return;
      if (!probe.get()) unexpectedAttempts.add(host + ":" + port);
      throw new SecurityException("Disposable acceptance denies non-allowlisted network connection");
    }
    @Override public void checkConnect(String host, int port, Object context) { checkConnect(host, port); }
  }
}
