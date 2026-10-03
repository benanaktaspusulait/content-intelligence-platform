# Part 02 Plan B1: Variant Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the already-migrated `video_variants` table (schema since `V1`) a real backend
surface — entity, repository, service, REST API — so a video's edit variants (original, hook,
trimmed, no-CTA, loop-cut, custom-edit) become a persisted, queryable identity instead of a
schema that has existed since the first migration but has never been written to or read by any
Java code.

**Architecture:** `VideoVariantEntity` is a plain JPA entity over the existing table (no schema
change). `VideoVariantRepository` is a standard Spring Data JPA repository. `VideoVariantService`
owns creation (validating the parent video exists, the `variantType` is one of the six allowed
values, and — for `parentVariantId` — that the referenced variant exists and belongs to the same
video) and listing. `VideoVariantController` exposes this at `/api/v1/videos/{videoId}/variants`,
following the existing `VideoController`'s REST conventions exactly (same package style, same
`EntityNotFoundException`-for-404 pattern, same DTO-record style).

**Tech Stack:** Java 21, Spring Boot, Spring Data JPA, Hibernate, PostgreSQL 17 (`video_variants`
table, unchanged since `V1__initial_schema.sql`), JUnit 5 + AssertJ, Mockito for repository mocks,
Testcontainers for one DB-constraint-focused test.

## Global Constraints

- Never edit a previously-committed migration (V1-V31). This plan requires **no new migration at
  all** — `video_variants` already has every column this plan needs.
- `video_variants.variant_type` has an existing DB-level CHECK constraint:
  `CHECK (variant_type IN ('ORIGINAL','HOOK_COLD_OPEN','TRIMMED','NO_CTA','LOOP_CUT','CUSTOM_EDIT'))`.
  The Java-side enum must use exactly these six names, in this exact spelling/case — do not invent
  a seventh value or rename any of the six.
- `video_variants.generated_path` has a DB-level `UNIQUE` constraint. The service layer must
  surface a clear validation error on a duplicate, not let a raw `DataIntegrityViolationException`
  leak to the API caller as an unstructured 500.
- `video_variants.parent_variant_id` is a nullable self-referential FK with no `ON DELETE` action
  specified in the migration (defaults to `NO ACTION` in Postgres) — a variant with children
  cannot be deleted while they exist. This plan does not implement delete at all (not needed by
  the audit's Phase B scope), so this constraint is inherited behavior, not something this plan
  needs to handle — do not add a delete endpoint as a result of noticing this.
- No fuzzy attribution anywhere in this plan's scope — a variant is always explicitly created
  against a specific `videoId`, never inferred from a filename or folder.
- Must leave the full Spring test suite green (`mvn test` from `intelligence/backend`).

---

## Context: the exact current schema this plan builds on

```sql
-- V1__initial_schema.sql, lines 34-41 (verbatim, do not re-run this — already applied)
CREATE TABLE video_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  parent_variant_id UUID REFERENCES video_variants(id),
  variant_type TEXT NOT NULL CHECK (variant_type IN ('ORIGINAL','HOOK_COLD_OPEN','TRIMMED','NO_CTA','LOOP_CUT','CUSTOM_EDIT')),
  generated_path TEXT NOT NULL UNIQUE,
  edit_operations JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Read these existing files in full before starting Task 1, to match this codebase's exact
conventions (do not guess at style — copy the real patterns):

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/creative/CreativeFingerprintEntity.java`
  — the closest existing example of a child entity with a `@ManyToOne` FK to `VideoEntity`, a
  `@GeneratedValue` UUID `id` (letting the DB's `gen_random_uuid()` default populate it), a JSONB
  column via `@JdbcTypeCode(SqlTypes.JSON)`, and a `@CreationTimestamp`-managed `createdAt`. This
  plan's `VideoVariantEntity` follows this exact shape, not `VideoEntity`'s shape (which manually
  assigns `id` and extends `AuditableEntity` — `video_variants` has no `entity_version`/
  `updated_at` columns, so `AuditableEntity` cannot be used here).
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoRepository.java`,
  `VideoService.java`, `api/VideoController.java`, `api/VideoDtos.java` — the exact REST/service/
  DTO conventions this plan's new `VideoVariantController`/`VideoVariantService`/variant DTOs must
  match: `EntityNotFoundException` for 404s, `IllegalArgumentException` for validation failures,
  package-visible controller methods (no explicit `public` on controller methods — confirm this by
  re-reading `VideoController.java`'s method signatures directly), `@RestController`/
  `@RequestMapping` at the class level with HTTP-verb-specific annotations per method.

---

## Task 1: `VideoVariantEntity` + `VideoVariantType` enum

**Files:**
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantType.java`
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantEntity.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantEntityPersistenceTest.java`

**Interfaces:**
- Consumes: `VideoEntity` (existing, unchanged).
- Produces: `VideoVariantType` enum with exactly 6 constants: `ORIGINAL`, `HOOK_COLD_OPEN`,
  `TRIMMED`, `NO_CTA`, `LOOP_CUT`, `CUSTOM_EDIT`. `VideoVariantEntity` with a no-arg protected
  constructor (JPA requirement) and a public constructor
  `VideoVariantEntity(VideoEntity video, VideoVariantEntity parentVariant, VideoVariantType variantType, String generatedPath, List<Object> editOperations)`,
  plus getters `getId()`, `getVideo()`, `getParentVariant()`, `getVariantType()`,
  `getGeneratedPath()`, `getEditOperations()`, `getCreatedAt()`.

- [ ] **Step 1: Write the failing test**

Read `CreativeFingerprintEntity.java` and the Testcontainers pattern in
`intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/ValidationEvidencePersistenceTest.java`
in full first (both already described above). Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantEntityPersistenceTest.java`:

```java
package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoVariantEntityPersistenceTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired VideoRepository videos;
  @Autowired VideoVariantRepository variants;

  private VideoEntity insertVideo(String relativePath) {
    return videos.save(
        new VideoEntity(
            UUID.randomUUID(),
            UUID.randomUUID().toString(),
            "test.mp4",
            relativePath,
            15000,
            1080,
            1920,
            30.0,
            0.5625,
            "h264",
            true,
            null,
            Instant.now()));
  }

  @Test
  void persistsAndReadsBackAVariantWithNoParent() {
    VideoEntity video = insertVideo("library/a.mp4");
    VideoVariantEntity variant =
        new VideoVariantEntity(
            video, null, VideoVariantType.ORIGINAL, "library/variants/a-original.mp4", List.of());

    VideoVariantEntity saved = variants.save(variant);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getVideo().getId()).isEqualTo(video.getId());
    assertThat(reloaded.getParentVariant()).isNull();
    assertThat(reloaded.getVariantType()).isEqualTo(VideoVariantType.ORIGINAL);
    assertThat(reloaded.getGeneratedPath()).isEqualTo("library/variants/a-original.mp4");
    assertThat(reloaded.getCreatedAt()).isNotNull();
  }

  @Test
  void persistsAVariantWithAParentVariant() {
    VideoEntity video = insertVideo("library/b.mp4");
    VideoVariantEntity original =
        variants.save(
            new VideoVariantEntity(
                video, null, VideoVariantType.ORIGINAL, "library/variants/b-original.mp4", List.of()));
    VideoVariantEntity hook =
        new VideoVariantEntity(
            video, original, VideoVariantType.HOOK_COLD_OPEN, "library/variants/b-hook.mp4", List.of());

    VideoVariantEntity saved = variants.save(hook);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getParentVariant().getId()).isEqualTo(original.getId());
  }

  @Test
  void rejectsADuplicateGeneratedPathAtTheDatabase() {
    VideoEntity video = insertVideo("library/c.mp4");
    variants.saveAndFlush(
        new VideoVariantEntity(
            video, null, VideoVariantType.ORIGINAL, "library/variants/shared-path.mp4", List.of()));
    VideoVariantEntity duplicate =
        new VideoVariantEntity(
            video, null, VideoVariantType.TRIMMED, "library/variants/shared-path.mp4", List.of());

    assertThatThrownBy(() -> variants.saveAndFlush(duplicate))
        .isInstanceOf(DataIntegrityViolationException.class);
  }

  @Test
  void persistsNonEmptyEditOperations() {
    VideoEntity video = insertVideo("library/d.mp4");
    VideoVariantEntity variant =
        new VideoVariantEntity(
            video,
            null,
            VideoVariantType.CUSTOM_EDIT,
            "library/variants/d-custom.mp4",
            List.of(java.util.Map.of("op", "trim", "startMs", 0, "endMs", 15000)));

    VideoVariantEntity saved = variants.saveAndFlush(variant);

    VideoVariantEntity reloaded = variants.findById(saved.getId()).orElseThrow();
    assertThat(reloaded.getEditOperations()).hasSize(1);
  }
}
```

(Note: this test references `VideoVariantRepository`, which does not exist until Task 2 — this is
intentional; Tasks 1 and 2 are tightly coupled enough that the brief writes Task 1's test against
the Task 2 repository rather than inventing a separate raw-`EntityManager`-based test just to keep
Task 1 artificially pure. Confirm this test file does not compile yet after Task 1 alone — that is
expected; it will compile and pass once Task 2 adds the repository. Do not skip ahead and implement
Task 2 as part of Task 1 — follow the two-task split for review-gate purposes, but it is fine that
Task 1's own test file does not independently build until Task 2 lands; note this in your report so
the reviewer understands the test's build dependency on the next task is not an API/scope leak.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantEntityPersistenceTest`
Expected: compilation failure — neither `VideoVariantEntity`, `VideoVariantType`, nor
`VideoVariantRepository` exist yet.

- [ ] **Step 3: Implement the enum**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantType.java`:

```java
package com.pompomhills.intelligence.video;

/**
 * Mirrors the {@code video_variants.variant_type} CHECK constraint in
 * {@code V1__initial_schema.sql} exactly - these six values are a database-enforced closed set,
 * not just a Java-side convenience. Do not add a seventh value here without a new migration
 * widening the CHECK constraint first.
 */
public enum VideoVariantType {
  ORIGINAL,
  HOOK_COLD_OPEN,
  TRIMMED,
  NO_CTA,
  LOOP_CUT,
  CUSTOM_EDIT
}
```

- [ ] **Step 4: Implement the entity**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantEntity.java`:

```java
package com.pompomhills.intelligence.video;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "video_variants")
public class VideoVariantEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "parent_variant_id")
  private VideoVariantEntity parentVariant;

  @Enumerated(EnumType.STRING)
  @Column(name = "variant_type", nullable = false)
  private VideoVariantType variantType;

  @Column(name = "generated_path", nullable = false, unique = true)
  private String generatedPath;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "edit_operations", nullable = false, columnDefinition = "jsonb")
  private List<Object> editOperations;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  protected VideoVariantEntity() {}

  public VideoVariantEntity(
      VideoEntity video,
      VideoVariantEntity parentVariant,
      VideoVariantType variantType,
      String generatedPath,
      List<Object> editOperations) {
    this.video = video;
    this.parentVariant = parentVariant;
    this.variantType = variantType;
    this.generatedPath = generatedPath;
    this.editOperations = editOperations;
  }

  public UUID getId() {
    return id;
  }

  public VideoEntity getVideo() {
    return video;
  }

  public VideoVariantEntity getParentVariant() {
    return parentVariant;
  }

  public VideoVariantType getVariantType() {
    return variantType;
  }

  public String getGeneratedPath() {
    return generatedPath;
  }

  public List<Object> getEditOperations() {
    return editOperations;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }
}
```

- [ ] **Step 5: Confirm the test still does not compile (expected at this point)**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantEntityPersistenceTest`
Expected: still a compilation failure, now specifically `cannot find symbol: class VideoVariantRepository`
— this confirms Task 1's own code is syntactically correct and the only remaining gap is Task 2's
repository, not a mistake in this task's files. Do not proceed to write `VideoVariantRepository`
yourself here — that is Task 2's deliverable, reviewed separately.

- [ ] **Step 6: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantType.java intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantEntity.java intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantEntityPersistenceTest.java
git commit -m "feat(intelligence): add VideoVariantEntity and VideoVariantType over the existing video_variants schema"
```

(This commit intentionally leaves the test file uncompilable until Task 2 lands — the full
`mvn test` run will fail at this point if run in isolation. This is expected and matches this
plan's explicit two-task split; Task 2's own Step 2 re-runs this exact test to confirm it compiles
and passes once the repository exists.)

---

## Task 2: `VideoVariantRepository`

**Files:**
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java`

**Interfaces:**
- Consumes: `VideoVariantEntity` (Task 1).
- Produces: `VideoVariantRepository extends JpaRepository<VideoVariantEntity, UUID>` with
  `List<VideoVariantEntity> findAllByVideoId(UUID videoId)` and
  `Optional<VideoVariantEntity> findByIdAndVideoId(UUID id, UUID videoId)` (the second method
  is how Task 3's service will verify a variant actually belongs to the video a caller claims it
  does, before returning or operating on it — never trust a bare `findById` for anything
  video-scoped).

- [ ] **Step 1: Implement**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java`:

```java
package com.pompomhills.intelligence.video;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoVariantRepository extends JpaRepository<VideoVariantEntity, UUID> {
  List<VideoVariantEntity> findAllByVideoId(UUID videoId);

  Optional<VideoVariantEntity> findByIdAndVideoId(UUID id, UUID videoId);
}
```

- [ ] **Step 2: Run Task 1's test to verify it now compiles and passes**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantEntityPersistenceTest`
Expected: all 4 tests PASS (this is the test written in Task 1, now unblocked by this repository).

- [ ] **Step 3: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java
git commit -m "feat(intelligence): add VideoVariantRepository with video-scoped lookup methods"
```

---

## Task 3: `VideoVariantService`

**Files:**
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantServiceTest.java`

**Interfaces:**
- Consumes: `VideoRepository.findById` (existing), `VideoVariantRepository` (Task 2),
  `VideoVariantEntity`/`VideoVariantType` (Task 1).
- Produces:
  - `VideoVariantService.create(UUID videoId, UUID parentVariantId, VideoVariantType variantType, String generatedPath, List<Object> editOperations) -> VideoVariantView`
  - `VideoVariantService.list(UUID videoId) -> List<VideoVariantView>`
  - `VideoVariantService.get(UUID videoId, UUID variantId) -> VideoVariantView`
  - `VideoVariantService.VideoVariantView` record:
    `(UUID id, UUID videoId, UUID parentVariantId, String variantType, String generatedPath, List<Object> editOperations, Instant createdAt)`
    (note: `variantType` is a `String` on the view — matching `VideoDtos.VideoResponse`'s existing
    convention of exposing enums as `.name()` strings on the API-facing shape, not the Java enum
    type itself).
  - `VideoVariantService.DuplicateGeneratedPathException` (new, extends `IllegalArgumentException`
    — thrown with a clear message when `generatedPath` collides with an existing row, translated
    from the underlying `DataIntegrityViolationException` so the controller layer never has to
    know about JPA/SQL exception types).

- [ ] **Step 1: Write the failing tests**

Read `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/IntelligenceQualityValidationServiceTest.java`
first for this codebase's exact bare-JUnit5+Mockito service-test convention (no Spring context,
manual `mock()`/`new Service(...)` construction) — this plan's service tests follow the identical
style. Create `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantServiceTest.java`:

```java
package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DataIntegrityViolationException;

class VideoVariantServiceTest {

  private VideoRepository videos;
  private VideoVariantRepository variants;
  private VideoVariantService service;

  @BeforeEach
  void setUp() {
    videos = mock(VideoRepository.class);
    variants = mock(VideoVariantRepository.class);
    service = new VideoVariantService(videos, variants);
  }

  private VideoEntity sampleVideo(UUID id) {
    return new VideoEntity(
        id,
        "hash-" + id,
        "test.mp4",
        "library/" + id + ".mp4",
        15000,
        1080,
        1920,
        30.0,
        0.5625,
        "h264",
        true,
        null,
        Instant.now());
  }

  @Test
  void createRejectsAVideoIdThatDoesNotExist() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(
            () ->
                service.create(
                    videoId, null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of()))
        .isInstanceOf(EntityNotFoundException.class);
  }

  @Test
  void createRejectsAParentVariantIdThatDoesNotBelongToTheSameVideo() {
    UUID videoId = UUID.randomUUID();
    UUID otherVideoId = UUID.randomUUID();
    UUID parentVariantId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    // The parent variant lookup is scoped to THIS video; it legitimately exists but under a
    // different video, so findByIdAndVideoId(parentVariantId, videoId) correctly returns empty.
    when(variants.findByIdAndVideoId(parentVariantId, videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(
            () ->
                service.create(
                    videoId,
                    parentVariantId,
                    VideoVariantType.HOOK_COLD_OPEN,
                    "library/b.mp4",
                    List.of()))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining(parentVariantId.toString());
    org.mockito.Mockito.verifyNoMoreInteractions(variants);
  }

  @Test
  void createPersistsAValidVariantAndReturnsItsView() {
    UUID videoId = UUID.randomUUID();
    VideoEntity video = sampleVideo(videoId);
    when(videos.findById(videoId)).thenReturn(Optional.of(video));
    ArgumentCaptor<VideoVariantEntity> captor = ArgumentCaptor.forClass(VideoVariantEntity.class);
    when(variants.save(captor.capture()))
        .thenAnswer(
            invocation -> {
              VideoVariantEntity entity = invocation.getArgument(0);
              java.lang.reflect.Field idField = VideoVariantEntity.class.getDeclaredField("id");
              idField.setAccessible(true);
              idField.set(entity, UUID.randomUUID());
              java.lang.reflect.Field createdAtField =
                  VideoVariantEntity.class.getDeclaredField("createdAt");
              createdAtField.setAccessible(true);
              createdAtField.set(entity, Instant.now());
              return entity;
            });

    var result =
        service.create(
            videoId, null, VideoVariantType.TRIMMED, "library/variants/trimmed.mp4", List.of());

    assertThat(result.videoId()).isEqualTo(videoId);
    assertThat(result.variantType()).isEqualTo("TRIMMED");
    assertThat(result.generatedPath()).isEqualTo("library/variants/trimmed.mp4");
    assertThat(result.parentVariantId()).isNull();
    assertThat(captor.getValue().getVideo()).isSameAs(video);
  }

  @Test
  void createTranslatesADuplicateGeneratedPathIntoADomainException() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.save(any()))
        .thenThrow(new DataIntegrityViolationException("duplicate key value"));

    assertThatThrownBy(
            () ->
                service.create(
                    videoId,
                    null,
                    VideoVariantType.ORIGINAL,
                    "library/already-taken.mp4",
                    List.of()))
        .isInstanceOf(VideoVariantService.DuplicateGeneratedPathException.class)
        .hasMessageContaining("library/already-taken.mp4");
  }

  @Test
  void listReturnsEmptyWhenNoVariantsExistForTheVideo() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.findAllByVideoId(videoId)).thenReturn(List.of());

    assertThat(service.list(videoId)).isEmpty();
  }

  @Test
  void listRejectsAVideoIdThatDoesNotExist() {
    UUID videoId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.list(videoId)).isInstanceOf(EntityNotFoundException.class);
    verify(variants, org.mockito.Mockito.never()).findAllByVideoId(any());
  }

  @Test
  void getRejectsAVariantIdThatDoesNotBelongToTheRequestedVideo() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    when(videos.findById(videoId)).thenReturn(Optional.of(sampleVideo(videoId)));
    when(variants.findByIdAndVideoId(variantId, videoId)).thenReturn(Optional.empty());

    assertThatThrownBy(() -> service.get(videoId, variantId))
        .isInstanceOf(EntityNotFoundException.class);
  }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantServiceTest`
Expected: compilation failure — `VideoVariantService` does not exist yet.

- [ ] **Step 3: Implement**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantService.java`:

```java
package com.pompomhills.intelligence.video;

import jakarta.persistence.EntityNotFoundException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VideoVariantService {
  private final VideoRepository videos;
  private final VideoVariantRepository variants;

  public VideoVariantService(VideoRepository videos, VideoVariantRepository variants) {
    this.videos = videos;
    this.variants = variants;
  }

  @Transactional
  public VideoVariantView create(
      UUID videoId,
      UUID parentVariantId,
      VideoVariantType variantType,
      String generatedPath,
      List<Object> editOperations) {
    VideoEntity video = requireVideo(videoId);
    VideoVariantEntity parentVariant =
        parentVariantId == null ? null : requireVariant(videoId, parentVariantId);
    VideoVariantEntity entity =
        new VideoVariantEntity(video, parentVariant, variantType, generatedPath, editOperations);
    VideoVariantEntity saved;
    try {
      saved = variants.save(entity);
    } catch (DataIntegrityViolationException error) {
      throw new DuplicateGeneratedPathException(generatedPath, error);
    }
    return map(saved);
  }

  @Transactional(readOnly = true)
  public List<VideoVariantView> list(UUID videoId) {
    requireVideo(videoId);
    return variants.findAllByVideoId(videoId).stream().map(this::map).toList();
  }

  @Transactional(readOnly = true)
  public VideoVariantView get(UUID videoId, UUID variantId) {
    requireVideo(videoId);
    return map(requireVariant(videoId, variantId));
  }

  private VideoEntity requireVideo(UUID videoId) {
    return videos
        .findById(videoId)
        .orElseThrow(() -> new EntityNotFoundException("Video not found: " + videoId));
  }

  private VideoVariantEntity requireVariant(UUID videoId, UUID variantId) {
    return variants
        .findByIdAndVideoId(variantId, videoId)
        .orElseThrow(
            () ->
                new IllegalArgumentException(
                    "Variant "
                        + variantId
                        + " does not exist or does not belong to video "
                        + videoId));
  }

  private VideoVariantView map(VideoVariantEntity entity) {
    return new VideoVariantView(
        entity.getId(),
        entity.getVideo().getId(),
        entity.getParentVariant() == null ? null : entity.getParentVariant().getId(),
        entity.getVariantType().name(),
        entity.getGeneratedPath(),
        entity.getEditOperations(),
        entity.getCreatedAt());
  }

  public record VideoVariantView(
      UUID id,
      UUID videoId,
      UUID parentVariantId,
      String variantType,
      String generatedPath,
      List<Object> editOperations,
      Instant createdAt) {}

  public static class DuplicateGeneratedPathException extends IllegalArgumentException {
    public DuplicateGeneratedPathException(String generatedPath, Throwable cause) {
      super("A variant with generatedPath '" + generatedPath + "' already exists", cause);
    }
  }
}
```

**Important note on `get()`'s exception type:** per Step 1's test
(`getRejectsAVariantIdThatDoesNotBelongToTheRequestedVideo`), `get()` throws
`EntityNotFoundException` (not `IllegalArgumentException`) when the variant doesn't belong to the
video — this differs deliberately from `create()`'s `requireVariant` call for `parentVariantId`,
which throws `IllegalArgumentException` (a parent-variant mismatch on create is a client input
error about a field the caller supplied; a `get()` miss is "this resource doesn't exist" in REST
terms, which should map to 404 not 400). Since both call sites use the same private
`requireVariant` helper which only throws `IllegalArgumentException`, `get()` must catch and
re-throw, or `requireVariant` needs to not be shared as literally as drafted. Resolve this
discrepancy before finalizing Step 3's code — read your own test file's two assertions
side-by-side (`createRejectsAParentVariantIdThatDoesNotBelongToTheSameVideo` expects
`IllegalArgumentException`; `getRejectsAVariantIdThatDoesNotBelongToTheRequestedVideo` expects
`EntityNotFoundException`) and implement whichever of the following you judge cleanest: (a) two
separate private helpers with different exception types, or (b) one helper returning
`Optional<VideoVariantEntity>` and each public method decides its own exception. Do not silently
pick one without noticing both tests make different claims — this is a real design decision the
brief's own draft code gets wrong (the draft above only throws `IllegalArgumentException` from
`requireVariant`, which would fail the `get()` test as drafted) — fix it, and note in your report
that you caught and corrected this.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantServiceTest`
Expected: all 7 tests PASS, including both exception-type tests with their distinct expected
types.

- [ ] **Step 5: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoVariantServiceTest.java
git commit -m "feat(intelligence): add VideoVariantService with video-scoped create/list/get and duplicate-path translation"
```

---

## Task 4: `VideoVariantController`

**Files:**
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantController.java`
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantDtos.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/api/VideoVariantControllerTest.java`

**Interfaces:**
- Consumes: `VideoVariantService` (Task 3), specifically `create`/`list`/`get` and
  `VideoVariantView`/`VideoVariantType`/`DuplicateGeneratedPathException`.
- Produces: REST endpoints
  - `POST /api/v1/videos/{videoId}/variants` → `VideoVariantDtos.VariantResponse`
  - `GET /api/v1/videos/{videoId}/variants` → `List<VideoVariantDtos.VariantResponse>`
  - `GET /api/v1/videos/{videoId}/variants/{variantId}` → `VideoVariantDtos.VariantResponse`

- [ ] **Step 1: Write the failing tests**

Read `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/IntelligenceQualityValidationControllerTest.java`
first for this codebase's controller-test convention (direct method invocation on the controller
instance for most cases, `MockMvc` only for the specific security-sensitive error-body checks —
this task does not have a prompt-text-leak concern like that file did, so plain direct-invocation
tests are sufficient here). Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/video/api/VideoVariantControllerTest.java`:

```java
package com.pompomhills.intelligence.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.video.VideoVariantService;
import com.pompomhills.intelligence.video.VideoVariantType;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class VideoVariantControllerTest {

  private VideoVariantService service;
  private VideoVariantController controller;

  @BeforeEach
  void setUp() {
    service = mock(VideoVariantService.class);
    controller = new VideoVariantController(service);
  }

  @Test
  void createDelegatesToTheServiceAndMapsTheResponse() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    var view =
        new VideoVariantService.VideoVariantView(
            variantId, videoId, null, "ORIGINAL", "library/a.mp4", List.of(), Instant.now());
    when(service.create(videoId, null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of()))
        .thenReturn(view);

    var request =
        new VideoVariantDtos.CreateVariantRequest(
            null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of());
    var response = controller.create(videoId, request);

    assertThat(response.id()).isEqualTo(variantId);
    assertThat(response.variantType()).isEqualTo("ORIGINAL");
  }

  @Test
  void listDelegatesToTheServiceAndMapsEveryResult() {
    UUID videoId = UUID.randomUUID();
    var view =
        new VideoVariantService.VideoVariantView(
            UUID.randomUUID(),
            videoId,
            null,
            "TRIMMED",
            "library/b.mp4",
            List.of(),
            Instant.now());
    when(service.list(videoId)).thenReturn(List.of(view));

    var response = controller.list(videoId);

    assertThat(response).hasSize(1);
    assertThat(response.get(0).variantType()).isEqualTo("TRIMMED");
  }

  @Test
  void getPropagatesTheServicesNotFoundException() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    when(service.get(videoId, variantId))
        .thenThrow(new jakarta.persistence.EntityNotFoundException("not found"));

    assertThatThrownBy(() -> controller.get(videoId, variantId))
        .isInstanceOf(jakarta.persistence.EntityNotFoundException.class);
  }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantControllerTest`
Expected: compilation failure — `VideoVariantController`/`VideoVariantDtos` do not exist yet.

- [ ] **Step 3: Implement the DTOs**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantDtos.java`:

```java
package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.video.VideoVariantType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class VideoVariantDtos {
  private VideoVariantDtos() {}

  public record CreateVariantRequest(
      UUID parentVariantId,
      @NotNull VideoVariantType variantType,
      @NotBlank String generatedPath,
      List<Object> editOperations) {}

  public record VariantResponse(
      UUID id,
      UUID videoId,
      UUID parentVariantId,
      String variantType,
      String generatedPath,
      List<Object> editOperations,
      Instant createdAt) {}
}
```

- [ ] **Step 4: Implement the controller**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantController.java`:

```java
package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.video.VideoVariantService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos/{videoId}/variants")
public class VideoVariantController {
  private final VideoVariantService service;

  public VideoVariantController(VideoVariantService service) {
    this.service = service;
  }

  @PostMapping
  VideoVariantDtos.VariantResponse create(
      @PathVariable UUID videoId,
      @Valid @RequestBody VideoVariantDtos.CreateVariantRequest request) {
    var view =
        service.create(
            videoId,
            request.parentVariantId(),
            request.variantType(),
            request.generatedPath(),
            request.editOperations() == null ? List.of() : request.editOperations());
    return map(view);
  }

  @GetMapping
  List<VideoVariantDtos.VariantResponse> list(@PathVariable UUID videoId) {
    return service.list(videoId).stream().map(this::map).toList();
  }

  @GetMapping("/{variantId}")
  VideoVariantDtos.VariantResponse get(
      @PathVariable UUID videoId, @PathVariable UUID variantId) {
    return map(service.get(videoId, variantId));
  }

  private VideoVariantDtos.VariantResponse map(VideoVariantService.VideoVariantView view) {
    return new VideoVariantDtos.VariantResponse(
        view.id(),
        view.videoId(),
        view.parentVariantId(),
        view.variantType(),
        view.generatedPath(),
        view.editOperations(),
        view.createdAt());
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=VideoVariantControllerTest`
Expected: all 3 tests PASS.

- [ ] **Step 6: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantController.java intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoVariantDtos.java intelligence/backend/src/test/java/com/pompomhills/intelligence/video/api/VideoVariantControllerTest.java
git commit -m "feat(intelligence): expose VideoVariantController REST API over the variant domain"
```

---

## Self-Review

**1. Spec coverage against the audit's Phase B item 1 ("Add backend access to `video_variants`
already present in the schema"):** fully covered — Task 1 (entity/enum), Task 2 (repository),
Task 3 (service with validation + duplicate-path translation), Task 4 (REST API). No new
migration needed, confirmed the existing schema already supports everything this plan needs.

**2. Placeholder scan:** no TBD/TODO patterns. The one deliberately-flagged open decision (Task
3's `get()` vs. `create()` exception-type discrepancy) is a genuine design decision left for the
implementer to resolve and document, not a placeholder — the brief explicitly shows the
discrepancy, names both failing tests, and asks for a judgment call with a documented resolution,
which is the correct way to flag a real ambiguity rather than silently guessing in the plan itself.

**3. Type consistency:** `VideoVariantView`'s field names (Task 3) are reused identically in
`VideoVariantDtos.VariantResponse` (Task 4) — `id`/`videoId`/`parentVariantId`/`variantType`/
`generatedPath`/`editOperations`/`createdAt`, same order, same types, across both records. The
`VideoVariantType` enum (Task 1) is used as the request-body type in `CreateVariantRequest` (Task
4) but surfaced as a `String` (`.name()`) in both `VideoVariantView` and `VariantResponse` — this
mirrors the existing codebase's own `VideoDtos.VideoResponse.status()` convention exactly (enum in,
string out), confirmed by re-reading `VideoService.map()`'s `v.getStatus().name()` call.
