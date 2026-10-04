# Part 02 Plan B2b: Frontend Variant Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Angular frontend's filename-suffix-guessing "variant" model
(`mediaVariant()`) with real, persisted `VideoVariant` identity from the backend, so a creative's
variants are something a user can see and act on as data, not something inferred from directory
layout and filename patterns.

**Architecture:** Three layers, in dependency order: (1) a small backend addition — resolve and
expose `variantId` on `GET /api/v1/videos/media-files`, since Plan B2a's audit-roadmap entry
promised this mirroring but it was never actually implemented; (2) new Angular service methods
(`VideoVariant` interface, `listVariants`, `createVariant`) consuming Plan B1's
`/api/v1/videos/{videoId}/variants` REST API, which currently has zero frontend callers; (3)
rewire `video-library.page.ts` and `video-detail.page.ts` to group/label by real `variantId`
instead of `mediaVariant()`, keeping the filename parser only as a fallback discovery label for
files that are not yet ingested (and therefore have no `variantId` to show).

**Tech Stack:** Spring Boot (Java 21), Angular 18 (standalone components, signals), Jasmine/Karma
for frontend tests, JUnit 5 + Testcontainers (`postgres:17-alpine`) for backend tests.

## Global Constraints

- Working directly on `master`, no worktree (binding user instruction: "masterdan her zaman devam
  et" — always work directly on master).
- Commit each reviewed task directly to master. No `--no-verify`, no force-push, no `git add -A`
  (stage named files only).
- Backend: `video_variants.variant_type` is a database-enforced CHECK constraint with exactly 6
  values (`ORIGINAL, HOOK_COLD_OPEN, TRIMMED, NO_CTA, LOOP_CUT, CUSTOM_EDIT`). Do not invent a 7th
  value anywhere in this plan.
- Backend: `video_variants.generated_path` is `unique`, same string shape as
  `MediaFile.relativePath` / `VideoEntity.relativePath` (a path relative to the configured data
  root). This plan relies on exact string equality between the two, not fuzzy matching — consistent
  with Plan B2a's established "no fuzzy matching" precedent for variant resolution.
  (`intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantEntity.java:35`,
  `.../video/api/VideoDtos.java:27-34`)
- No new Flyway migration is needed in this plan — only a new repository query method against the
  existing `video_variants` table (next free migration number is `V34` if that assumption turns out
  wrong; confirm by listing `intelligence/backend/src/main/resources/db/migration/` before Task 1).
- Frontend: standalone Angular components, `OnPush` change detection, native `signal`/`computed`,
  template literals inline in `@Component({ template: ... })` — follow the exact style already in
  `video-library.page.ts` and `video-detail.page.ts` (no new UI framework, no new HTTP client
  wrapper).
- Frontend tests use `TestBed` + `provideHttpClientTesting()`/`HttpTestingController` for the
  service, and `TestBed` + `provideRouter([])` + a mocked `CreativeIntelligenceService` object for
  the two page components — follow `creative-intelligence.service.spec.ts`,
  `video-library.page.spec.ts`, and `video-detail.page.spec.ts` exactly (do not introduce
  `HttpClientTestingModule`, which is deprecated in this Angular version).
- Known mismatch to resolve, not paper over: `VideoVariantType` enum values (`ORIGINAL,
  HOOK_COLD_OPEN, TRIMMED, NO_CTA, LOOP_CUT, CUSTOM_EDIT`) do not align 1:1 with `mediaVariant()`'s
  string labels (`'HD'`, `'No Text'`, `'Hook End Card Test'` have no enum equivalent). This plan
  does not try to force an alignment — ingested files show their real persisted `variantType`
  (humanized), un-ingested files keep showing the filename-guessed label with a visible "not yet
  linked" distinction. See Task 3 for the exact rule.

---

## File Structure

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java`
  — add `Optional<VideoVariantEntity> findByGeneratedPath(String generatedPath)`.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java` —
  add `variantId` field to the `MediaFile` record.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java` —
  resolve `variantId` in `mapMediaFile()` using the new repository method.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServiceMediaFilesVariantTest.java`
  (new) — Testcontainers test proving `mediaFiles()` resolves `variantId` for a file whose path
  matches a persisted variant's `generatedPath`, and leaves it `null` otherwise.
- `intelligence/frontend/src/app/core/creative-intelligence.service.ts` — add `VideoVariant`
  interface, `listVariants(videoId)`/`createVariant(videoId, request)` methods; add `variantId:
  string | null` to the `MediaFile` interface.
- `intelligence/frontend/src/app/core/creative-intelligence.service.spec.ts` — add tests for the
  two new methods.
- `intelligence/frontend/src/app/pages/video-library.page.ts` — replace `mediaVariant()`-only
  grouping key with a `variantId`-first grouping key; keep `mediaVariant()` as the un-ingested
  fallback label (exported function stays, used differently).
- `intelligence/frontend/src/app/pages/video-library.page.spec.ts` — add tests for the new grouping
  behavior.
- `intelligence/frontend/src/app/pages/video-detail.page.ts` — replace the `variants` computed's
  `mediaVariant()`-only grouping with real `VideoVariant` data fetched via `listVariants()`, mapped
  onto the folder's `MediaFile[]` by `variantId`/`relativePath`.
- `intelligence/frontend/src/app/pages/video-detail.page.spec.ts` — add tests for the new variant
  rail behavior.

---

### Task 1: Backend — resolve `variantId` on `GET /api/v1/videos/media-files`

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java:27-34`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoService.java:154-197,291-300`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/video/VideoServiceMediaFilesVariantTest.java`

**Interfaces:**
- Consumes: `VideoVariantEntity.getId(): UUID`, `VideoVariantEntity.getGeneratedPath(): String`
  (both already exist, see `VideoVariantEntity.java`).
- Produces: `VideoVariantRepository.findByGeneratedPath(String): Optional<VideoVariantEntity>` (new
  method, used by Task 1 only in this plan, but a reasonable general-purpose lookup). `MediaFile`
  gains a `variantId` field — this is what Task 2's Angular `MediaFile` interface mirrors, and what
  Task 4's `video-library.page.ts` grouping key and Task 5's `video-detail.page.ts` variant rail
  both key off.

**Context:** `VideoService.mediaFiles()` currently resolves two things per file: whether it is
`ingested` (via `VideoRepository.findAllByRelativePathIn` + the `video_path_aliases` table from
Plan B2a Task 1) and, if so, the `VideoEntity`. It never looks at `video_variants` at all. Every
`video_variants.generated_path` is a relative path string that *is* some file's `relativePath` by
construction (that's how a variant gets rendered to disk) — so resolving `variantId` for a
`MediaFile` is a direct `generated_path` lookup, no new concept needed.

- [ ] **Step 1: Write the failing test**

```java
package com.pompomhills.intelligence.video;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.video.api.VideoDtos.MediaFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class VideoServiceMediaFilesVariantTest {

  @Container
  static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17-alpine");

  @DynamicPropertySource
  static void configure(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
  }

  @Autowired private VideoService videoService;
  @Autowired private VideoRepository videos;
  @Autowired private VideoVariantRepository variants;
  @Autowired private com.pompomhills.intelligence.video.VideoDataProperties properties;

  private Path dataRoot;

  @BeforeEach
  void setUp() throws Exception {
    dataRoot = properties.dataRoot().toAbsolutePath().normalize();
    Files.createDirectories(dataRoot.resolve("library/VariantMediaFileTest"));
  }

  @Test
  void mediaFilesResolvesVariantIdWhenGeneratedPathMatchesAFile() throws Exception {
    Path original = dataRoot.resolve("library/VariantMediaFileTest/original.mp4");
    Path hookCut = dataRoot.resolve("library/VariantMediaFileTest/hook_cut.mp4");
    Files.write(original, new byte[] {1, 2, 3});
    Files.write(hookCut, new byte[] {4, 5, 6});

    VideoEntity video =
        videos.save(
            new VideoEntity(
                "original.mp4",
                "library/VariantMediaFileTest/original.mp4",
                1000L,
                1080,
                1920,
                30.0,
                0.5625,
                "h264",
                true));
    VideoVariantEntity variant =
        variants.save(
            new VideoVariantEntity(
                video,
                null,
                VideoVariantType.HOOK_COLD_OPEN,
                "library/VariantMediaFileTest/hook_cut.mp4",
                List.of()));

    List<MediaFile> files = videoService.mediaFiles("library/VariantMediaFileTest", false);

    MediaFile hookFile =
        files.stream().filter(file -> file.name().equals("hook_cut.mp4")).findFirst().orElseThrow();
    assertThat(hookFile.variantId()).isEqualTo(variant.getId());

    MediaFile originalFile =
        files.stream().filter(file -> file.name().equals("original.mp4")).findFirst().orElseThrow();
    assertThat(originalFile.variantId()).isNull();
  }
}
```

Note: check `VideoEntity`'s actual constructor signature in
`intelligence/backend/src/main/java/com/pompomhills/intelligence/video/VideoEntity.java` before
writing this test — if its constructor differs from the 9-arg form assumed above, use whatever
existing test in the same package (e.g. `VideoServiceTest.java` or
`VideoPathAliasEntityPersistenceTest.java`) already constructs a `VideoEntity`, and copy its exact
pattern instead of guessing.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServiceMediaFilesVariantTest`
Expected: FAIL (compile error — `MediaFile.variantId()` does not exist yet).

- [ ] **Step 3: Add `findByGeneratedPath` to the repository**

```java
package com.pompomhills.intelligence.video;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoVariantRepository extends JpaRepository<VideoVariantEntity, UUID> {
  List<VideoVariantEntity> findAllByVideoId(UUID videoId);

  Optional<VideoVariantEntity> findByIdAndVideoId(UUID id, UUID videoId);

  Optional<VideoVariantEntity> findByGeneratedPath(String generatedPath);
}
```

- [ ] **Step 4: Add `variantId` to the `MediaFile` record**

In `VideoDtos.java`, change:

```java
  public record MediaFile(
      String name,
      String relativePath,
      Long sizeBytes,
      Instant modifiedAt,
      boolean ingested,
      UUID videoId,
      String status) {}
```

to:

```java
  public record MediaFile(
      String name,
      String relativePath,
      Long sizeBytes,
      Instant modifiedAt,
      boolean ingested,
      UUID videoId,
      String status,
      UUID variantId) {}
```

- [ ] **Step 5: Resolve `variantId` in `VideoService`**

In `VideoService.java`, inject `VideoVariantRepository` via the constructor (add a field and
constructor parameter alongside the existing `videos`/`pathAliases`/`ml`/`properties` fields — read
the existing constructor first and follow its exact style). Then update `mapMediaFile`:

```java
  private MediaFile mapMediaFile(Path root, Path file, Map<String, VideoEntity> ingestedByPath) {
    String relativePath = root.relativize(file).toString();
    VideoEntity ingested = ingestedByPath.get(relativePath);
    UUID variantId =
        variants.findByGeneratedPath(relativePath).map(VideoVariantEntity::getId).orElse(null);
    return new MediaFile(
        file.getFileName().toString(),
        relativePath,
        fileSize(file),
        lastModified(file),
        ingested != null,
        ingested == null ? null : ingested.getId(),
        ingested == null ? null : ingested.getStatus().name(),
        variantId);
  }
```

(Field name `variants` for the injected `VideoVariantRepository` — confirm this doesn't collide
with an existing field of the same name in `VideoService.java` before applying; rename to
`variantRepository` if it does.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd intelligence/backend && mvn test -Dtest=VideoServiceMediaFilesVariantTest`
Expected: PASS (2 assertions: hook file resolves the variant's UUID, original file resolves null).

- [ ] **Step 7: Run full backend suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass (103 + 1 new = 104). Pay particular attention to any existing test that
constructs a `MediaFile` positionally (record constructor) — the new trailing `variantId` parameter
will break positional construction anywhere it's not using a builder-style helper. Fix any such
call site directly (add `null` as the final argument) rather than leaving it broken.

- [ ] **Step 8: Commit**

```bash
cd intelligence/backend
git add src/main/java/com/pompomhills/intelligence/video/VideoVariantRepository.java \
        src/main/java/com/pompomhills/intelligence/video/api/VideoDtos.java \
        src/main/java/com/pompomhills/intelligence/video/VideoService.java \
        src/test/java/com/pompomhills/intelligence/video/VideoServiceMediaFilesVariantTest.java
git commit -m "feat(intelligence): resolve variantId on the media-files listing endpoint"
```

(Also stage any additional call-site fixes from Step 7 in the same commit, since they're required
for the build to pass.)

---

### Task 2: Frontend service — `VideoVariant` interface, `listVariants`, `createVariant`, `MediaFile.variantId`

**Files:**
- Modify: `intelligence/frontend/src/app/core/creative-intelligence.service.ts`
- Test: `intelligence/frontend/src/app/core/creative-intelligence.service.spec.ts`

**Interfaces:**
- Consumes: Task 1's backend `MediaFile.variantId` field (now present in the JSON response) and
  Plan B1's existing `VideoVariantDtos.VariantResponse(UUID id, UUID videoId, UUID
  parentVariantId, String variantType, String generatedPath, List<Object> editOperations, Instant
  createdAt)` shape from `GET/POST /api/v1/videos/{videoId}/variants`.
- Produces: `VideoVariant` interface, `listVariants(videoId: string): Observable<VideoVariant[]>`,
  `createVariant(videoId: string, request: CreateVariantRequest): Observable<VideoVariant>` — all
  three consumed by Task 5 (`video-detail.page.ts`). `MediaFile.variantId: string | null` —
  consumed by Task 4 (`video-library.page.ts`) and Task 5.

- [ ] **Step 1: Write the failing tests**

Append to `creative-intelligence.service.spec.ts` (new `describe` block, same file, same
`provideHttpClient()`/`provideHttpClientTesting()` pattern as the existing block):

```typescript
describe('CreativeIntelligenceService variants', () => {
  let service: CreativeIntelligenceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CreativeIntelligenceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists variants for a video', () => {
    const response: VideoVariant[] = [{
      id: 'variant-1', videoId: 'video-1', parentVariantId: null,
      variantType: 'HOOK_COLD_OPEN', generatedPath: 'library/x/hook.mp4',
      editOperations: [], createdAt: '2026-10-04T00:00:00Z',
    }];

    service.listVariants('video-1').subscribe(variants => expect(variants).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/variants');
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });

  it('creates a variant for a video', () => {
    const response: VideoVariant = {
      id: 'variant-2', videoId: 'video-1', parentVariantId: 'variant-1',
      variantType: 'TRIMMED', generatedPath: 'library/x/trimmed.mp4',
      editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }], createdAt: '2026-10-04T00:00:00Z',
    };

    service.createVariant('video-1', {
      parentVariantId: 'variant-1', variantType: 'TRIMMED',
      generatedPath: 'library/x/trimmed.mp4', editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }],
    }).subscribe(variant => expect(variant).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/variants');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      parentVariantId: 'variant-1', variantType: 'TRIMMED',
      generatedPath: 'library/x/trimmed.mp4', editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }],
    });
    request.flush(response);
  });
});
```

Add `VideoVariant` and `CreateVariantRequest` to the file's import line from
`'./creative-intelligence.service'` at the top of the spec file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/creative-intelligence.service.spec.ts'`
Expected: FAIL (compile error — `VideoVariant`, `CreateVariantRequest`, `listVariants`,
`createVariant` don't exist yet).

- [ ] **Step 3: Add the `VideoVariant` interface and `variantId` to `MediaFile`**

In `creative-intelligence.service.ts`, change:

```typescript
export interface MediaFile {
  name: string;
  relativePath: string;
  sizeBytes: number | null;
  modifiedAt: string | null;
  ingested: boolean;
  videoId: string | null;
  status: string | null;
}
```

to:

```typescript
export interface MediaFile {
  name: string;
  relativePath: string;
  sizeBytes: number | null;
  modifiedAt: string | null;
  ingested: boolean;
  videoId: string | null;
  status: string | null;
  variantId: string | null;
}

export type VariantType = 'ORIGINAL' | 'HOOK_COLD_OPEN' | 'TRIMMED' | 'NO_CTA' | 'LOOP_CUT' | 'CUSTOM_EDIT';

export interface VideoVariant {
  id: string;
  videoId: string;
  parentVariantId: string | null;
  variantType: string;
  generatedPath: string;
  editOperations: unknown[];
  createdAt: string;
}

export interface CreateVariantRequest {
  parentVariantId: string | null;
  variantType: VariantType;
  generatedPath: string;
  editOperations: unknown[];
}
```

(`VideoVariant.variantType` stays `string`, not `VariantType`, because it's a read value coming
back from the server — matches the existing convention in this file where response interfaces use
plain `string` for enum-backed fields, e.g. `VideoApiRecord.status`, `PredictionApiRecord.platform`.
`CreateVariantRequest.variantType` is the narrower `VariantType` since it's a value this code
constructs itself.)

- [ ] **Step 4: Add `listVariants` and `createVariant` methods**

Add near `ingestVideo` (same section of the class, video-identity-related methods):

```typescript
  listVariants(videoId: string): Observable<VideoVariant[]> {
    return this.http.get<VideoVariant[]>(`${this.baseUrl}/videos/${videoId}/variants`);
  }

  createVariant(videoId: string, request: CreateVariantRequest): Observable<VideoVariant> {
    return this.http.post<VideoVariant>(`${this.baseUrl}/videos/${videoId}/variants`, request);
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/creative-intelligence.service.spec.ts'`
Expected: PASS (all tests in the file, old + 2 new).

- [ ] **Step 6: Run full frontend suite for regressions**

Run: `cd intelligence/frontend && npx ng test --watch=false`
Expected: all tests pass. The `MediaFile` interface gained a required field (`variantId`), so any
spec file constructing a literal `MediaFile` object (`video-library.page.spec.ts`,
`video-detail.page.spec.ts`, and this file's own fixtures if any) will fail to compile until updated
— fix each one directly by adding `variantId: null` (or an explicit test value where the test is
about variants) to every existing `MediaFile` literal, rather than leaving the suite red.

- [ ] **Step 7: Commit**

```bash
cd intelligence/frontend
git add src/app/core/creative-intelligence.service.ts src/app/core/creative-intelligence.service.spec.ts \
        src/app/pages/video-library.page.spec.ts src/app/pages/video-detail.page.spec.ts
git commit -m "feat(intelligence): add VideoVariant service methods and MediaFile.variantId"
```

(Adjust the staged file list to match whichever spec files Step 6 actually required touching.)

---

### Task 3: `video-library.page.ts` — group by `variantId` first, filename-guess only as fallback

**Files:**
- Modify: `intelligence/frontend/src/app/pages/video-library.page.ts`
- Test: `intelligence/frontend/src/app/pages/video-library.page.spec.ts`

**Interfaces:**
- Consumes: `MediaFile.variantId: string | null` (Task 2).
- Produces: no exported signature changes — `mediaVariant(filename: string): string` keeps its
  exact existing name/signature/behavior (still used, just no longer the primary grouping key),
  consumed as-is by Task 5's `video-detail.page.ts`.

**Context:** Today, `displayFiles`'s grouping key is `` `${parentPath}|${mediaVariant(file.name)}` ``
— purely filename-derived. The fix is minimal and surgical: when `file.variantId` is present, use it
directly as (part of) the grouping key and as the row label (humanized from a lookup table, not the
filename guess); when it's `null` (file not yet ingested, or ingested but no `VideoVariant` row
exists for it yet — e.g. the original file before any edit was ever registered as a variant), fall
back to exactly what happens today. This preserves every existing passing test in the file (the
`mediaVariant`-driven ones) while fixing the real-identity case.

- [ ] **Step 1: Write the failing test**

Add to `video-library.page.spec.ts`, in the top-level fixtures, a file with a `variantId` and
extend the existing `displayFiles` exercise. Add a new focused test:

```typescript
describe('variant identity grouping', () => {
  const service = {
    getMediaDirectories: () => of(folders),
    getMediaFiles: () =>
      of([
        { ...shared, name: 'take1.mp4', relativePath: 'library/Sea Stories/take1.mp4', variantId: 'variant-1' },
        { ...shared, name: 'weird_name_v9.mp4', relativePath: 'library/Sea Stories/weird_name_v9.mp4', variantId: 'variant-1' },
      ]),
    ingestDirectory: () => of({ relativeDirectory: '', discovered: 0, ingested: [], errors: [] }),
    ingestVideo: () => of({}),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VideoLibraryPage],
      providers: [provideRouter([]), { provide: CreativeIntelligenceService, useValue: service }],
    }).compileComponents();
  });

  it('groups two differently-named files under the same real variant into one row group', () => {
    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();

    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    const choice = fixture.nativeElement.querySelector('.folder-option input') as HTMLInputElement;
    choice.click();
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('.media-files-table tbody tr');
    expect(rows.length).toBe(2);
    expect(rows[0].querySelector('td strong').textContent).toBe(rows[1].querySelector('td strong').textContent);
  });
});
```

Note: `shared`'s existing definition in the file lacks `variantId` — Task 2's Step 6 should already
have added `variantId: null` to it; confirm this before writing this test, don't duplicate the fix.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-library.page.spec.ts'`
Expected: FAIL — both rows currently get *different* `variantName` labels (`'Original'` for
`take1.mp4`, `'V9 ' + whatever mediaVariant() guesses` for `weird_name_v9.mp4`), since grouping is
still filename-only.

- [ ] **Step 3: Add a variantId-aware grouping key**

This page only has `MediaFile.variantId` available (not `variantType` strings — that requires a
second fetch per video via `listVariants()`, which Task 4 does for the detail page but is out of
scope here, since the library page lists files across many videos at once and a per-row variant-type
fetch would mean one HTTP call per file). So this task's fix is deliberately narrow: keep each row's
**label** exactly as `mediaVariant(file.name)` today (no visual change to label text), but change the
**grouping/counting key** to prefer real `variantId` identity when present, falling back to the
existing filename-guess key when it's `null`. Add this exported helper near `mediaVariant`:

```typescript
export function variantGroupKey(file: MediaFile, folderPath: string): string {
  return file.variantId ? `variant:${file.variantId}` : `guess:${folderPath}|${mediaVariant(file.name)}`;
}
```

Replace the two call sites inside `displayFiles` in the class body:

```typescript
  protected readonly displayFiles = computed<MediaFileView[]>(() => {
    const totals = new Map<string, number>();
    const positions = new Map<string, number>();
    for (const file of this.mediaFiles()) { const key = variantGroupKey(file, this.parentPath(file.relativePath)); totals.set(key, (totals.get(key) || 0) + 1); }
    return this.mediaFiles().map(file => {
      const folderPath = this.parentPath(file.relativePath);
      const variant = mediaVariant(file.name);
      const key = variantGroupKey(file, folderPath);
      const position = (positions.get(key) || 0) + 1;
      positions.set(key, position);
      const suffix = (totals.get(key) || 0) > 1 ? `${variant} ${position}` : variant;
      const folderName = this.readableFolder(folderPath);
      return { ...file, folderName, folderPath, variantName: suffix, displayName: `${folderName} · ${suffix}` };
    });
  });
```

Note this still uses `mediaVariant(file.name)` for the **label text** (unchanged visual behavior for
single-file groups), but the **grouping/counting** (`totals`, `positions`, duplicate-suffix numbering)
is now driven by real identity when available. Two files sharing a `variantId` land in the same
`key` and get sequential labels (`"Original 1"`/`"Original 2"` style, exactly like today's existing
duplicate-label handling) instead of silently appearing as two unrelated single-file groups.

Revise the test from Step 1 to assert this precisely — the two same-`variantId` files should produce
2 rows that share one row group (not 2 groups), with sequential suffixes if labels collide, e.g.:

```typescript
  it('groups two differently-named files under the same real variant into one row group', () => {
    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();
    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    const choice = fixture.nativeElement.querySelector('.folder-option input') as HTMLInputElement;
    choice.click();
    fixture.detectChanges();

    const groups = fixture.nativeElement.querySelectorAll('.media-file-group');
    expect(groups.length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.media-files-table tbody tr').length).toBe(2);
  });
```

(`groupMediaFilesByFolder` already groups by `folderPath`, which both fixture files share, so this
specific test exercises `displayFiles`'s totals/positions change rather than `groupMediaFilesByFolder`
itself — the point being proven is the duplicate-counting/suffixing, which the existing
`groupMediaFilesByFolder` tests do not cover.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-library.page.spec.ts'`
Expected: PASS (new test + all pre-existing tests in the file still pass unchanged, since
`variantGroupKey` falls back to the exact pre-existing filename-guess key whenever `variantId` is
null, which is every fixture in every pre-existing test in this file).

- [ ] **Step 5: Run full frontend suite for regressions**

Run: `cd intelligence/frontend && npx ng test --watch=false`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd intelligence/frontend
git add src/app/pages/video-library.page.ts src/app/pages/video-library.page.spec.ts
git commit -m "fix(intelligence): group media files by real variantId when available"
```

---

### Task 4: `video-detail.page.ts` — real `VideoVariant` list drives the "Compare variants" rail

**Files:**
- Modify: `intelligence/frontend/src/app/pages/video-detail.page.ts`
- Test: `intelligence/frontend/src/app/pages/video-detail.page.spec.ts`

**Interfaces:**
- Consumes: `CreativeIntelligenceService.listVariants(videoId): Observable<VideoVariant[]>` (Task
  2), `MediaFile.variantId: string | null` (Task 2).
- Produces: no new exports — `VariantView` keeps its existing shape (`extends MediaFile { label:
  string }`), consumers outside this file are none (it's a private interface).

**Context:** Today, `variants` is a pure computed signal over `this.files()` (the folder's
`MediaFile[]`) using only `mediaVariant(file.name)`. The brief here is: once a file is ingested
(`activeFile().ingested === true`, meaning it has a `videoId`), fetch that video's real
`VideoVariant[]` via `listVariants()` and use `variantType` (humanized) as the label for any
`MediaFile` whose `variantId` matches a fetched variant's `id`; files with no `variantId` (not yet
ingested, or ingested but never explicitly registered as a variant — e.g. a video that predates
Plan B1) keep the existing `mediaVariant()` filename-guess label. This is additive — the rail must
never show nothing just because variants haven't loaded yet or the list is empty.

- [ ] **Step 1: Write the failing test**

Add to `video-detail.page.spec.ts`, extend `serviceWith`/add a new describe block:

```typescript
describe('VideoDetailPage variant rail', () => {
  const route = {
    paramMap: of(convertToParamMap({})),
    queryParamMap: of(convertToParamMap({ folder: 'library/Giant Sock', file: mediaFile.relativePath })),
  };

  const taggedFile: MediaFile = { ...mediaFile, variantId: 'variant-1' };

  function serviceWithVariants() {
    return {
      mediaContentUrl: () => '/media',
      getMediaFiles: () => of([taggedFile]),
      getVideo: () => of(video),
      getReachFurther: () => of(null),
      getTrajectory: () => of({ videoId: 'video-1', platform: 'facebook', label: '', cleanOrganic: true, interventions: [], points: [] }),
      getPlatformGrowth: () => of(null),
      getDiscoveryProfile: () => of(baseDiscovery),
      listVariants: () => of([{
        id: 'variant-1', videoId: 'video-1', parentVariantId: null,
        variantType: 'HOOK_COLD_OPEN', generatedPath: taggedFile.relativePath,
        editOperations: [], createdAt: '2026-10-04T00:00:00Z',
      }]),
    };
  }

  it('labels a variant-linked file with its real persisted variant type, not a filename guess', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithVariants() },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const rail = fixture.nativeElement.querySelector('.variant-list');
    expect(rail.textContent).toContain('Hook / Cold Open');
    expect(rail.textContent).not.toContain('HD');
  });

  afterEach(() => TestBed.resetTestingModule());
});
```

(`mediaFile.name` is `'giant-sock-hd.mp4'`, which `mediaVariant()` would label `'HD'` — this is the
exact case the test's negative assertion (`not.toContain('HD')`) is pinning down: real variant
identity must override the filename guess once it's available.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-detail.page.spec.ts'`
Expected: FAIL — `rail.textContent` contains `'HD'` (today's filename-only label), not `'Hook /
Cold Open'`, and `listVariants` is never called (service mock has no effect yet).

- [ ] **Step 3: Import the variant label map and fetch real variants**

In `video-detail.page.ts`, import `VideoVariant` alongside the existing imports from
`'../core/creative-intelligence.service'`. Add a shared label map (same values as Task 3's, kept in
sync — duplicate the small `Record` rather than cross-importing between two page files, which is
the established pattern in this codebase: `video-detail.page.ts` already imports only
`mediaVariant` as a function from `video-library.page.ts`, not shared constants):

```typescript
const VARIANT_TYPE_LABELS: Record<string, string> = {
  ORIGINAL: 'Original',
  HOOK_COLD_OPEN: 'Hook / Cold Open',
  TRIMMED: 'Trimmed',
  NO_CTA: 'No CTA',
  LOOP_CUT: 'Loop Cut',
  CUSTOM_EDIT: 'Custom Edit',
};
```

Add a signal to hold fetched variants:

```typescript
  protected readonly videoVariants = signal<VideoVariant[]>([]);
```

Rewrite the `variants` computed:

```typescript
  protected readonly variants = computed<VariantView[]>(() => {
    const variantTypeById = new Map(this.videoVariants().map(variant => [variant.id, variant.variantType]));
    const labelFor = (file: MediaFile): string => {
      const type = file.variantId ? variantTypeById.get(file.variantId) : undefined;
      return type ? (VARIANT_TYPE_LABELS[type] ?? type) : mediaVariant(file.name);
    };
    const totals = new Map<string, number>();
    const positions = new Map<string, number>();
    for (const file of this.files()) { const base = labelFor(file); totals.set(base, (totals.get(base) || 0) + 1); }
    return this.files().map(file => {
      const base = labelFor(file);
      const position = (positions.get(base) || 0) + 1;
      positions.set(base, position);
      return { ...file, label: (totals.get(base) || 0) > 1 ? `${base} ${position}` : base };
    });
  });
```

Fetch variants whenever a video becomes active. In `activateVariant`, after `this.video.set(video);
this.loadPerformance();` (both occurrences — the `knownVideo` branch and the `getVideo` subscribe
branch), add a call to a new private helper:

```typescript
  private activateVariant(file: MediaFile, knownVideo?: VideoApiRecord): void {
    this.activeFile.set(file); this.message.set(''); this.video.set(null); this.clearPerformance();
    if (!file.ingested || !file.videoId) { this.videoVariants.set([]); return; }
    if (knownVideo?.id === file.videoId) { this.video.set(knownVideo); this.loadPerformance(); this.loadVariants(file.videoId); return; }
    this.service.getVideo(file.videoId).subscribe({ next: video => { if (this.activeFile()?.relativePath === file.relativePath) { this.video.set(video); this.loadPerformance(); this.loadVariants(video.id); } }, error: response => this.message.set(response.error?.message || 'Technical metadata could not be loaded.') });
  }

  private loadVariants(videoId: string): void {
    this.service.listVariants(videoId).subscribe({ next: variants => this.videoVariants.set(variants), error: () => this.videoVariants.set([]) });
  }
```

(Fail-open to the filename-guess label on any `listVariants` error — this is a display enhancement,
not a load-blocking dependency; the page must stay usable if the variants endpoint is unreachable.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd intelligence/frontend && npx ng test --watch=false --include='**/video-detail.page.spec.ts'`
Expected: PASS (new test + all pre-existing tests in the file, since `videoVariants` defaults to
`[]`, making `variantTypeById` empty and `labelFor` fall back to `mediaVariant(file.name)` for every
pre-existing fixture that has no `variantId`).

- [ ] **Step 5: Run full frontend suite for regressions**

Run: `cd intelligence/frontend && npx ng test --watch=false`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
cd intelligence/frontend
git add src/app/pages/video-detail.page.ts src/app/pages/video-detail.page.spec.ts
git commit -m "feat(intelligence): drive the variant comparison rail from real VideoVariant data"
```

---

### Task 5: Final whole-plan review + roadmap doc update

**Files:**
- Modify: `intelligence/docs/superpowers/PART_02_COMPLETION_ROADMAP.md` (mark Plan B2b complete,
  same style as the existing "✅" rows for A/B1/B2a).

- [ ] **Step 1: Re-run both full suites one more time from a clean checkout state**

```bash
cd intelligence/backend && mvn test
cd intelligence/frontend && npx ng test --watch=false
```

Expected: both green. This is the whole-plan regression gate, independent of each task's own
per-task run.

- [ ] **Step 2: Dispatch (or perform directly) a focused whole-plan review**

Verify, across all 4 implementation tasks together:
- `MediaFile.variantId` is resolved identically on the backend (`generated_path` exact-match) and
  consumed identically on both frontend pages (variantId-first, filename-guess fallback) — no
  silent divergence between Task 3's and Task 4's fallback logic.
- No path in `video-library.page.ts` or `video-detail.page.ts` ever shows a blank/undefined label —
  every branch terminates in either a real humanized `variantType` or the pre-existing
  `mediaVariant()` guess, never `undefined`/`''`.
- `listVariants`/`createVariant` match Plan B1's actual deployed REST contract byte-for-byte (re-
  check `VideoVariantController.java`/`VideoVariantDtos.java` directly, don't trust this plan's
  copy if the controller has changed since this plan was written).
- `VideoVariantType`'s 6-value closed set is respected everywhere a `VariantType` literal is used
  (`CreateVariantRequest` in the service); no 7th value introduced.
- Scope boundary: no file outside `intelligence/backend/.../video/` and `intelligence/frontend/`
  was touched by this plan.

- [ ] **Step 3: Update the roadmap doc**

In `PART_02_COMPLETION_ROADMAP.md`, change the B2b row's status from `⬜ Not started` to `✅ Done`
(match the exact formatting already used for the A/B1/B2a rows), and add one or two sentences under
the existing Plan B2b detail section (same place as Plan A's "2 documented follow-up gaps" note)
recording: (a) the `MediaFile.variantId` backend gap found during investigation (roadmap had assumed
Plan B2a added it; it hadn't — this plan added it instead), (b) that `video-library.page.ts`'s
per-file *label* still uses `mediaVariant()` guessing even when `variantId` is known (only the
*grouping key* changed), which is an intentional scope boundary for this plan, not an oversight —
flag it as a candidate for a future small follow-up if a real per-group `variantType` label becomes
a product requirement there too.

- [ ] **Step 4: Commit**

```bash
git add intelligence/docs/superpowers/PART_02_COMPLETION_ROADMAP.md
git commit -m "docs(intelligence): mark Part 02 Plan B2b complete (frontend variant consumption)"
```

---

## Self-Review Notes (for the plan author, not a task)

- Spec coverage: roadmap's 3 B2b bullets (new `VideoVariant` interface + HTTP methods; `MediaFile`
  gains `variantId`; replace `mediaVariant()` filename-parser consumption in both pages) are covered
  by Tasks 2, 1+2, and 3+4 respectively.
- Discovered gap handled, not papered over: roadmap assumed Plan B2a added backend `variantId`
  resolution; verified directly against `VideoDtos.java`/`VideoService.java` that it had not; added
  Task 1 to close that gap as part of this plan, consistent with how Plan B2a itself absorbed
  unplanned-but-necessary scope when its own investigation found gaps.
- Type consistency checked: `VideoVariant`/`CreateVariantRequest` (Task 2) match
  `VideoVariantDtos.VariantResponse`/`CreateVariantRequest` (already-built Java, re-read directly
  from source in this plan's investigation) field-for-field; `MediaFile.variantId` (Task 2) matches
  the Java `MediaFile.variantId` field added in Task 1; `VariantView` (Task 4, pre-existing) is
  unchanged in shape, only in how its `label` is computed.
