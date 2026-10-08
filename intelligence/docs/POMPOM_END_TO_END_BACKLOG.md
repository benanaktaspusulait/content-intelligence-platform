# Pompom Hills — kanıt temelli uygulama iş listesi

8 Ekim 2026. Bu liste [mevcut sistem denetimi](POMPOM_END_TO_END_AUDIT.md) sonucudur; **hiçbir madde bu audit içinde uygulanmadı**. Önce mevcut TODO/roadmap okundu: root `TODO.md` Meta/publisher kapsamına aittir; connector işleri o sahibin akışında kalır. `docs/superpowers/PART_01_COMPLETION_ROADMAP.md` Plan D/E/F canonical evidence/authorization/fixability bileşenleri reuse edilir. Phase4 learning spec niyeti açıklar, çalışan retrieval kanıtı değildir. Eski tamamlandı checkmark'ları yeni uçtan uca acceptance yerine kullanılmaz.

## Öncelik, minimum release ve sıralama

P0: yanlış kaynak/lineage, core import correction kesintisi ve false training success. P1: günlük gerekli orkestrasyon/öğrenme/kurtarma sınırları. P2: açıklama/verimlilik/yerel workspace sağlamlığı. P3: advanced trained prediction. Effort S/M/L göreli; dış servis ve eski veri belirsizlikleri nedeniyle sabit teslim tarihi yok.

**Minimum günlük kullanım release:** B01+B02+B04 route-consistency+B13 → B04 review-restore+B09 → B03+B05 → B06+B07+B10 → B08+B16. Mevcut prompt'u aç/değerlendir, boundedfix/revalidate, prompt+video actualreview, originals/versions preserved, manualedit/import veya justifiedregen handoff,verifiedlesson retrieval ve exactperformance association birlikte acceptance almalı. B11 newstory flow takip eden aynı ürün release'inde çalışmalı; existingprompt yolunun bitmesini bekleten tek giriş kapısı yapılmamalı. B12/B15'daki root/evidence blocker gerçek kuruluma engelse ilgili küçük alt sonuç minimum release'e çekilir.

Critical path: exact source identity B01 → stable review route B04 → bounded repair B03 → canonical profile admission B10 → parent-linked generation B07. Retrieval B08 B03/B11 request contract'ını, audience lesson eligibility B16'yı tüketir. Basic verified prompt-fix retrieval audience data beklemeden başlayabilir. Live-provider stage B14 ayrıca açık kapsam/bütçe ister. Gerçek statisticaltraining B17 minimum release'ten ayrıdır.

Bağımsız işler: B02 import UI ve B13 training honesty farklı dosya sahipleriyle paralel yapılabilir. B09 jobs ile B06 edit handoff ayrı modüller; video/variant identity DTO'su önce B01/B07 sahibiyle dondurulmalı. B03/B04/B05/B08 aynı WorkflowService/component üzerinde aynı anda koordinasyonsuz edit yapmamalı; tek owner, contract-first sequential integration. Meta/publisher dosyaları başka stream sahibine bırakılır. Yeni worktree önerilmiyor; kullanıcının master/ana dizin isteği geçerli.

| ID | Öncelik | İş | Journey | Effort |
|---|---|---|---|---|
| [B01](#b01) | P0 | Kesin prompt–video kimliğini koru; aynı klasör ve en yeni sürümü generation gerçeği sayma | B/C/D/F | M; historical link audit belirsizliği var |
| [B02](#b02) | P0 | Analytics import ekranındaki boş eşleştirme seçicisini çalıştır ve exact variant seçtir | G | S–M |
| [B03](#b03) | P1 | UI üzerinden kalıcı ve bounded minimal repair→yeni sürüm→bağımsız revalidation oturumu | B/F | L; stop/session identity belirsizlikleri |
| [B04](#b04) | P0 | Kayıtlı post-family incelemeyi içerik/sürümle yeniden aç ve prompt+video ekranını bağla | B/C/F | M |
| [B05](#b05) | P1 | Prompt olmadan actual-video review ve reconstruction provenance | C/D | M |
| [B06](#b06) | P1 | Manual veya lab edit sonucunu UI’dan parent variant olarak içe al ve tekrar incele | E/C | M |
| [B07](#b07) | P1 | Mevcut videodan yeniden üretim talebini exact parent/prompt/attempt soyuna bağla | F/C | L |
| [B08](#b08) | P1 | Onaylı ilgili dersleri sonraki prompt/onarıma gerçekten getir ve provenance göster | A/B/F | M |
| [B09](#b09) | P1 | Analiz işi requested-version kimliğini ve crash recovery yolunu tamamla | C/D/J6 | M–L |
| [B10](#b10) | P1 | İçerik profili uygulanabilirliğini canonical final admission kararına kadar taşı | B/C/F | L; owner interface review required |
| [B11](#b11) | P1 | İsteğe bağlı story/production-prompt rollerini mevcut içerik akışına bağla | A/B/F | L |
| [B12](#b12) | P2 | Kalan F10 belirsizliğinde eksik kaynak kanıtını görünür ve düzeltilebilir kıl | B/C | S–M |
| [B13](#b13) | P0 | Gerçek model üretilmediğinde training/promotion başarı iddiasını kaldır | ML/operator trust | S–M |
| [B14](#b14) | P2 | Rol ve video sağlayıcılarını açık bütçeli ayrı canlı contract testinde doğrula | A/B/F | M; provider/account variability |
| [B15](#b15) | P2 | Media-root/format/rename/empty-folder davranışını tek tutarlı workspace contract yap | A/B/D | M |
| [B16](#b16) | P1 | Analytics context-aware dedup, correction provenance ve batch reopen | G/learning | M |
| [B17](#b17) | P3 | Yeterli veri olduğunda gerçek eğitim artifact/registry/inference bağını kur | advanced prediction | L/uncertain; no fixed delivery estimate |

## B01

**Kesin prompt–video kimliğini koru; aynı klasör ve en yeni sürümü generation gerçeği sayma**

- **Priority / journey / effort:** P0; B/C/D/F; M; historical link audit belirsizliği var.
- **Observed current behavior:** VideoCreativeContextService FOLDER_SOURCE sorgusu birden fazla candidate arasından version/time sırasıyla LIMIT1 seçiyor. SourceResolver ayrıca aynı path için latest stored rawText kullanıyor. Canonical render_asset bağlantısı varken kesin sürüm elde ediliyor; import/variant tarafında bu garanti yok.
- **Expected behavior / root cause:** Exact render lineage veya operatörün kanıtlı seçimi gösterilmeli; candidate set >1 olduğunda AMBIGUOUS kalmalı. Disk hash değişince stored source snapshot yeni generation kaynağı diye sunulmamalı.
- **Code/UI evidence and components to reuse:** E03/E05/E06; V39/V40; existing ContentPromptQueryService, VideoPromptSourceResolver, render_asset→render_job join. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Mevcut resolver/context contract ve persisted manual resolution üzerinde küçük düzeltme; contentId/promptVersionId/hash/provenance UI görünürlüğü. Kalibrasyon, parser yaratıcı semantiği, Meta matcher değişimi kapsam dışı.
- **Dependencies:** Yok; sonraki B04/B05/B07/B16 bunu tüketir.
- **Acceptance criteria / required behavioral tests / UI acceptance:** İki prompt/two versions/one video fixture; same-folder belirsizlik; stale source hash; exact rendered version survives newer prompt; copied variant parent. UI: ambiguous klip aç, candidate gerekçelerini gör, exact sürümü seç, yenile, aynı bağı koru; aksi halde fidelity UNKNOWN.
- **Migration/data compatibility:** Eski inferred links silinmez; confidence/provenance ayrımı additive migration ile korunur, backfill dry-run ve operatör teyidi gerekir.
- **External prerequisite:** Sahibin gerçekten hangi prompt ile ürettiği bilinmeyen medyada açık manuel seçim.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B02

**Analytics import ekranındaki boş eşleştirme seçicisini çalıştır ve exact variant seçtir**

- **Priority / journey / effort:** P0; G; S–M.
- **Observed current behavior:** Gerçek CSV UI preview200/rows200,1unresolved; combobox yalnız Select video… içeriyor. ImportDataPage videos signal [] kalıyor; list loader yok. Component/API helper yalnız videoId gönderiyor.
- **Expected behavior / root cause:** Mevcut canonical videos/variants yüklenmeli; exact video+variant seçimi ve gerekçesi persist edilmeli; unresolved satır kaybolmamalı.
- **Code/UI evidence and components to reuse:** E23/E24; import-ui.har, ui-import-preview.txt; PerformanceImportServiceVariantTest; existing /videos, /videos/{id}/variants, match endpoint. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Angular import loader/selection contract; existing backend variant mapping reuse. Yeni Meta/provider client, fuzzy matching, yaklaşık görüş sayısını doğrulanmış horizon yapma kapsam dışı.
- **Dependencies:** B01 exact identity contract; video selector loader bağımsız başlanabilir.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Backend/video loader success/error/pagination, multiple variants, mismatch rejection, large string publication ID. UI: CSV yükle→satır seç→video+variant seç→gerekçe→preview güncelle→commit→yeniden aç exact ilişkiyi gör; duplicate import yeni observation üretmesin.
- **Migration/data compatibility:** V33 matched_variant_id ve mevcut observation contracts reuse; eski video-only kayıtları original/unknown provenance ile açıkça göster.
- **External prerequisite:** Doğrulanmış publication ID eksikse unmatched kalması doğru; gerçek eşleştirmeyi kullanıcı yapar.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B03

**UI üzerinden kalıcı ve bounded minimal repair→yeni sürüm→bağımsız revalidation oturumu**

- **Priority / journey / effort:** P1; B/F; L; stop/session identity belirsizlikleri.
- **Observed current behavior:** Local patch 1pass/up to3patches ve final review var; API fixture version6→7 çalıştı. Latest prompt save ayrı UI eylemi. Legacy ML auto-fix templates default5; OpenAI minimal repair ve best-candidate session yok.
- **Expected behavior / root cause:** Tek start action; configurable default en çok2 provider repair attempt; independent validation; original/patch/all findings/cost/stop reason sakla; tolerant-only, evidence-needed, intent-change, plateau/oscillation/limits/provider failure/cancel stopları. Latest otomatik best olmasın.
- **Code/UI evidence and components to reuse:** E09–13/E38; repair-fixture-api.json; existing prompt versions, workflow append-only events, canonical validation and provider-neutral adapter; Part01 roadmap Plan F fixability ile ilişkilendir. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Mevcut backend workflow içine bir orchestrator/session; yeni platform/microservice/fixer self-approval/otomatik render kapsam dışı. Local patch yolu manual seçenek olarak kalmalı.
- **Dependencies:** B01/B04; provider role contract B11 ile paylaşılan port, ücretli runtime verify B14 sonraki ayrı aşama.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Fixture provider meaningful fix, unfixable evidence-only, essential removal reject,0improvement,repeat/cycle,second attempt/cancel/timeout; new version independently validated and accepted best retained. UI: existing prompt seç→Fix→durum/diff/cost→accept/reject→reopen stable session→final version+validation IDs.
- **Migration/data compatibility:** V46/V47 geçmiş kayıtları değiştirmeden new session/version fields; eski one-pass ledger ile adapter; concurrency unique keys ve retry no duplicate versions/cost.
- **External prerequisite:** Gerçek OpenAI erişimi ve açık bütçe yalnız canlı doğrulama için; mock acceptance önce.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B04

**Kayıtlı post-family incelemeyi içerik/sürümle yeniden aç ve prompt+video ekranını bağla**

- **Priority / journey / effort:** P0; B/C/F; M.
- **Observed current behavior:** Route content/version text koruyor; profile reset FROZEN; latest impact review/QA gösterilmiyor. LoadSourceIntent sadece intent/creativeEvidence alıyor. Direct contentVersion DTO sourcePath içermediğinden bağlı video seçimi boş. Gerçek fixture UI patch/save version8 oluşturdu; URL version6 kaldı ve refresh eski prompt'u açtı (repair-ui.har + ui-repair-save-reload.txt).
- **Expected behavior / root cause:** Save başarılı olduğunda route yeni promptVersionId ile güncellenmeli; refresh seçili sürümü değiştirmemeli. Geçerli saved review/QA IDs ve settings görünür; cached/reused vs new run ayrımı; source/version/video/snapshot açık. Değişmiş prompt/settings/ref invalidates admission; page refresh paid call başlatmaz.
- **Code/UI evidence and components to reuse:** E02/E08/E13/E40; ui-review-reopen*.txt; current recordGET/list and four reviewDimensions reuse. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Quality/detail and video/context route/read DTO links; existing default frozen semantics korunur; UI explicit profile choice persisted provenance. Yeni validator veya paid refresh kapsam dışı.
- **Dependencies:** B01; B03 session read contract; bağımsız read UI ilk hazırlanabilir.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Saved result loads without POST; route version mismatch/error visible; changed reference/duration/model/intent stale; exact QA bound actual video. UI: open content/version→select operational profile→review→refresh/direct URL→same result/date/model/video; Reanalyze yeni runID gösterir.
- **Migration/data compatibility:** Eski kayıt policyVersion farklıysa historical read-only, new assessment gerektiği görünür; no rewrite.
- **External prerequisite:** Yok.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B05

**Prompt olmadan actual-video review ve reconstruction provenance**

- **Priority / journey / effort:** P1; C/D; M.
- **Observed current behavior:** Deterministic VideoService/analysis çalışabilir, plan semantic incomplete gösterilir. Impact actualQa requires prior current source review ID; reconstructed candidate/original ayrımı bağlı workflow yok.
- **Expected behavior / root cause:** Prompt unavailable/ambiguous durumuyla actual evidence review çalışsın; fidelity NOT_EVALUATED/UNKNOWN gerekçeli; viewer usability available evidence kadar. Optional reconstructed candidate ayrı origin, original diye atanmasın.
- **Code/UI evidence and components to reuse:** E05/E14/E15/E22; ui-actual-video.txt; existing video IDs/hash/time, effect reviewer, observations allowlist. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Mevcut actualQA contract için optional explicit lineage state, source-resolution UI; yeni VLM pipeline zorunlu değil. Kaynaksız ESSENTIAL/fidelity PASS uydurma kapsam dışı.
- **Dependencies:** B01/B04.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Absent/ambiguous plan; actual usability supporting human clip evidence without fake fidelity; reconstruction labeled and never overwrites original. UI: video import/select→prompt unavailable→actual findings→choose recommendation→optional candidate association→reopen.
- **Migration/data compatibility:** Additive provenance field; legacy plan-linked QA unchanged; immutable prior records.
- **External prerequisite:** Gerçek semantic judgment için klip incelemesi; ücretli VLM yalnız ayrı B14 izin/bütçe.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B06

**Manual veya lab edit sonucunu UI’dan parent variant olarak içe al ve tekrar incele**

- **Priority / journey / effort:** P1; E/C; M.
- **Observed current behavior:** Lab CLI trim_start/trim_end/remove_black_tail ve rescue edit üretir; backend variant parent check/list var. Angular action bir edit result oluşturup parent/hash/review bağlantısını taşımaz.
- **Expected behavior / root cause:** Supported edit önerisi→original immutable→manual/lab handoff→new variant verified path/hash/operations→actual review; edit gerçekten uygulanmış dosya ile kanıtlanmalı.
- **Code/UI evidence and components to reuse:** E30/E33; VideoVariantServiceTest; lab fix_engine/rescue_edit/ffmpeg_tools and existing video rail. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** İlk release manual edit/import handoff olabilir; mevcut lab motoru reuse. Yeni full editor, frame interpolation, generative edit, publisher kapsam dışı.
- **Dependencies:** B01/B04/B05; B07 shares parent lineage interface.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Original hash unchanged, no cross-video parent, output file/hash exists, duplicate safe, after trim real duration, review new variant. UI: öneri→handoff→edited file register→old/new compare→fresh findings→no old audience attached.
- **Migration/data compatibility:** Existing video_variants additive source/hash/provenance links; existing paths retained; orphan media error visible.
- **External prerequisite:** Manual editor/FFmpeg available; no paid generation.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B07

**Mevcut videodan yeniden üretim talebini exact parent/prompt/attempt soyuna bağla**

- **Priority / journey / effort:** P1; F/C; L.
- **Observed current behavior:** Queue/admission/job snapshots/idempotency/attempts var; final operation gated. Impact recommendation ve prompt repair mevcut original video/edit variant ile tek regeneration journey oluşturmaz; edited variant lacks exact render/prompt FK.
- **Expected behavior / root cause:** Material essential loss justified→new prompt version→new canonical validation→explicit refs/model/duration/cost→authorized separate render attempt parent linked→new output→compare. Old variant/performance aynen kalmalı.
- **Code/UI evidence and components to reuse:** E14/E18–21/E33; queue policy tests, V10/attempt migrations, existing RenderDashboard and ContentPromptSnapshot. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Mevcut queue request/lineage/UI handoff; auth değişmeden add parent reference. Segment-only repair mevcut worker full-video olduğundan desteklenmiyorsa açıkça reddet; yeni generator client kapsam dışı.
- **Dependencies:** B01/B03/B04/B10; provider live acceptance B14 ayrı.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Mock denied null/unknown/stale before credits; authorized fixture creates separate attempt with parent; idempotent replay no new submit; output import exact prompt version. UI: select failed event→reason→repair→version→settings/cost→explicit queue→compare original/new (mock service only).
- **Migration/data compatibility:** Additive parent source/variant/attempt FK or equivalent immutable relation; existing jobs historical unknown parent retained.
- **External prerequisite:** Canonical visual/independent evidence and provider budget for actual render; not authorized by audit.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B08

**Onaylı ilgili dersleri sonraki prompt/onarıma gerçekten getir ve provenance göster**

- **Priority / journey / effort:** P1; A/B/F; M.
- **Observed current behavior:** Workflow LESSON/EXPERIMENT/LEARNING_REVIEW records/list var; automaticallyApplied=false. Review/repair/provider calls do not query or inject prior approved lessons; no ranking/revocation use path.
- **Expected behavior / root cause:** Evidence-verified context/model/version/settings/profile/duration eligible lessons retrieved; revoked/stale/unverified excluded; prompt includes references and operator explanation. One failed render universal rule olmasın.
- **Code/UI evidence and components to reuse:** E08–10/E25; existing append-only ledger and learning-review. Phase4 learning spec supporting intent only; production read path missing. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Structured/text retrieval first; current provider request construction integration; learned guidance advisory and canonical validation retained. Vector DB, model weight training, auto ruleset editing kapsam dışı.
- **Dependencies:** B03/B11 provider request port + B01 fixed lineage + B16 credible outcomes; prompt-fix examples can begin without audience labels.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Verified relevant prior repair changes next fixture provider request with record ID; unverified/rejected/revoked/version-incompatible examples excluded; deterministic retrieval budget/ranking. UI: inspect prior lesson→approve→new eligible request→used lesson provenance→revoke→next request excludes.
- **Migration/data compatibility:** Append approval/revocation events instead of mutable history; legacy records ineligible until evidence verified.
- **External prerequisite:** Gerçek confirmed lesson corpus; sample scarcity explicit.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B09

**Analiz işi requested-version kimliğini ve crash recovery yolunu tamamla**

- **Priority / journey / effort:** P1; C/D/J6; M–L.
- **Observed current behavior:** Analysis jobs durable active-video unique and failed retry var. enqueue checks default current analysis not requested analysisVersion; RUNNING rows never reclaimed by queue worker.10jobtests:7pass3fixture failures.
- **Expected behavior / root cause:** Compatible complete analysis identity; force/new request distinct/reused status; lease/checkpoint/reconcile after process death; no blind duplicate external paid request; actionable failed/cancel/retry state.
- **Code/UI evidence and components to reuse:** E22; backend-test-results.json; tests stub creative-v1 and wrong-overload cause. Reuse existing job tables and render lease design; don’t duplicate workers. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Video analysis job contract/key/recovery; fix invalid fixtures as separate test corrections after authorization. Prediction/provider architecture and legacy freeze kapsam dışı.
- **Dependencies:** B01/B04 identity visibility; interface can be developed independently.
- **Acceptance criteria / required behavioral tests / UI acceptance:** RequestedV4 vsV5 cache distinction, duplicate concurrent requests same identity, crash after claim/call/result checkpoint, timeout ambiguity, failed retry bounds; correct mocked overload. UI: Analyze vs Reanalyze→restart→same job or documented safe recovery→no doubled cost.
- **Migration/data compatibility:** Additive lease/identity uniqueness migration with active-row reconciliation; old RUNNING rows require explicit safe recovery strategy.
- **External prerequisite:** Provider reconciliation semantics for ambiguous paid calls; default no resubmission.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B10

**İçerik profili uygulanabilirliğini canonical final admission kararına kadar taşı**

- **Priority / journey / effort:** P1; B/C/F; L; owner interface review required.
- **Observed current behavior:** Post-family execution heuristic warning/context projection works. Queue still requires legacy validation status/blockerCount/criticalCount + exact canonical auth; optional-specialist blockers may remain. Additive post-family gate cannot remove historical counts.
- **Expected behavior / root cause:** Canonical versioned projection knows applicable vs nonapplicable vs unknown for selected profile; required safety/source/identity/visual/freshness/revalidation unchanged. New-path AUTHORIZED proof must include final queue, not review alone.
- **Code/UI evidence and components to reuse:** E16/E18–20/E39; synthetic impact tests and queue tests; existing Family8 policy owner; Part01 Plan D/E evidence/control interface. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Versioned canonical policy/evidence mapping and admission contract, coordinated with frozen-family owner; frozen Family1–10 baseline/semantics and bypass toggle kapsam dışı.
- **Dependencies:** B01/B04; needed before live positive B07/B14.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Curiosity two-character reveal/no mandatory comedy/3attempts/full-frame0 cause is not blocked solely by inapplicable rows; actual essential/safety failure blocked; UNKNOWN evidence still pending; exact canonical AUTHORIZED plus refs/hash/settings to queue with mockcredits.
- **Migration/data compatibility:** Historical validations remain same; new policyVersion in identity; incompatible old auth stale; no backfill green status.
- **External prerequisite:** Frozen policy ownership and an actual complete reference/evidence fixture.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B11

**İsteğe bağlı story/production-prompt rollerini mevcut içerik akışına bağla**

- **Priority / journey / effort:** P1; A/B/F; L.
- **Observed current behavior:** New prompt manual folder/title/editor exists; no DeepSeek story alternatives or OpenAI production builder/repair callsite found. Optional critic DeepSeek/OpenAI text-only is a separate role.
- **Expected behavior / root cause:** Configured DeepSeek concept/story when requested; OpenAI construction/minimal repair; validation independent. Existing prompt never forced through story generation. Missing config explicit; no silent substitution.
- **Code/UI evidence and components to reuse:** E01–03/E37–38; llm/provider.py adapters; workflow provider port and caption service remain separate. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Existing content/story candidate version interface and provider-neutral role config; alternatives/select/edit UI. New microservice, caption/publishing rewrite, VLM claims for text model kapsam dışı.
- **Dependencies:** B01/B03/B08 contracts; new story is not critical path for already-written prompt.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Mock role routing hits requested provider/model; schema-invalid/timeouts/retries/cost/provenance; image/video unsupported explicitly rejected; existing prompt repair performs0story calls. UI: folder/name/idea→requested alternatives→choose/edit→prompt version→validate.
- **Migration/data compatibility:** New story revision provenance additive; old manual contents remain valid with MANUAL origin.
- **External prerequisite:** DeepSeek/OpenAI credentials and budget for B14 live-role verification.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B12

**Kalan F10 belirsizliğinde eksik kaynak kanıtını görünür ve düzeltilebilir kıl**

- **Priority / journey / effort:** P2; B/C; S–M.
- **Observed current behavior:** Current adapter9real sources:7RISKY2UNKNOWN; legacy path differs. Box Cat/Spot Cat source scope incomplete; manual labels are not evaluator inputs.
- **Expected behavior / root cause:** Each UNKNOWN explains missing source/extraction/schema/consumer or legitimate uncertainty; operator can add exact source-bound structured evidence and recompute same family semantics. Do not forcePASS.
- **Code/UI evidence and components to reuse:** E35; family10-current-source-probe.json; existing structuredPlan/source-span enrichment. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Existing evidence UI/coverage/extraction diagnostics only; B10 handles canonical wiring. New calibration program, Gold lookup, winner lookup, baseline modifications kapsam dışı.
- **Dependencies:** B04; B10 for decision consumption.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Missing entity/held-object scope remainsUNKNOWN; grounded added clause populates finding; invalid source span rejected; true unsupported effect unknown; UI shows requirement/source quote/method/coverage.
- **Migration/data compatibility:** Preserve old reports; evidence version/hash invalidates new snapshot.
- **External prerequisite:** Authoritative source/reference evidence where actually missing.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B13

**Gerçek model üretilmediğinde training/promotion başarı iddiasını kaldır**

- **Priority / journey / effort:** P0; ML/operator trust; S–M.
- **Observed current behavior:** 30empty synthetic rows HTTP200 CHALLENGER_CREATED; endpoint performs no fit/save/split/eval. Registry promotion changes DB status while prediction hardcodes cold-start-baseline-v1.
- **Expected behavior / root cause:** Return honest training unavailable/notimplemented or explicit dataset-readiness status until real artifact exists; promotion cannot imply active trained inference; cold-start remains transparently labeled.
- **Code/UI evidence and components to reuse:** E26–29; ml-training-inference-probe.json; Models page; current registry/prediction DTOs. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Honest service response/UI and promotion readiness checks first; no training implementation in minimal release. B17 later learns actual model.
- **Dependencies:** Yok.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Empty/invalid rows never create trained-success claim; missing artifact/eval cannot promote operational inference; genuine coldstart returns null target/sample0. UI: models/readiness shows unavailable/not trained, no green learned prediction; exported responses honest.
- **Migration/data compatibility:** Existing metadata retained as historical registrations, not deleted; status/provenance additive; callers handling old status documented.
- **External prerequisite:** Yok; real dataset only B17.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B14

**Rol ve video sağlayıcılarını açık bütçeli ayrı canlı contract testinde doğrula**

- **Priority / journey / effort:** P2; A/B/F; M; provider/account variability.
- **Observed current behavior:** OpenArt cached model/mode schema and mocks exist; no paid calls in audit.2.5image2video lacksaspectRatio; worker one480pvideo. Current optional critic disabled by default; source capability metadata is not live completion proof.
- **Expected behavior / root cause:** Display checked provider/modelID/mode/date; exact duration/aspect/ref/cost request provenance; account availability errors; bounded live-role calls only with user scope/budget. Supported and unverified separate.
- **Code/UI evidence and components to reuse:** E17/E21/E36/E37; provider-capabilities.json; existing CliRealOpenArtAdapter and SemanticModelRoutingPolicy. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Reuse current adapters; configure/check test account, provider doc/schema verification, mock first. No duplicate client or enable provider switch as part of audit.
- **Dependencies:** B03/B07/B10/B11 as applicable; routing fixture tests can precede live.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Mock unsupportedduration/missingrefs/aspect/upgrade/timeout/cost ceiling explicit; actual scoped call logs exact model/request/evidence usage/cost and result. UI: settings visible before consent, no automatic fallback, firstframe acquisition distinct from videoauth.
- **Migration/data compatibility:** New capability snapshot immutable and binding versioned; old snapshot remains readable.
- **External prerequisite:** Explicit budget/user authorization/test account and current official/provider metadata; never infer from display names.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B15

**Media-root/format/rename/empty-folder davranışını tek tutarlı workspace contract yap**

- **Priority / journey / effort:** P2; A/B/D; M.
- **Observed current behavior:** UI hardcodes production root; isolated rooterrors whilelibraryAPI200. Scanner reads selected .txt/.md names, resolver also .json/.yaml; folder creationASCII-only; fullyempty folder omitted nextscan; pathidentity rename gap.
- **Expected behavior / root cause:** Configured allowed roots visible; explicit no-video/emptyfolder can reopen; compatible supported formats; Unicode names safe; moves/aliases reconcile without duplicating source content.
- **Code/UI evidence and components to reuse:** E02–04/E06; workspace API probes; V32/V39; actual scanner/source import reuse. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Root selection/config contract and idempotent path-alias import; no original file rewriting/migration repair; full storage redesign out of scope.
- **Dependencies:** B01 identity; emptyfolder/root UI independently possible.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Unicode spaces/Turkish names, permitted path canonicalization, alias duplicate bytes, move/stalefiles,2prompts2videos ambiguity; UI create emptyfolder→refresh stillvisible→select prompt-only→import version exacthash.
- **Migration/data compatibility:** Keep content IDs/source versions; additive prompt path aliases; audit dry-run before mapping oldpaths.
- **External prerequisite:** Mounted root access; symlink policy deliberately preserved rather than bypassed.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B16

**Analytics context-aware dedup, correction provenance ve batch reopen**

- **Priority / journey / effort:** P1; G/learning; M.
- **Observed current behavior:** Preview dedup checks filehash before platform/timezone; identical bytes under changed context can return oldbatch. UI batch state signal-only; match video-only; corrected exports differenthash no demonstrated correctionworkflow.
- **Expected behavior / root cause:** Same source/context replay idempotent; changed platform/timezone explicit conflict/new provenance; corrected exports retain correction_of lineage; exact variant, units/null/time/window visible; lifetime never fabricatedfixedhorizon.
- **Code/UI evidence and components to reuse:** E23–24/E34; V2/V33; existing raw imports/observations/trajectories and variant-scoped tests; Meta improvements reused from TODO owning stream. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Existing import/observation contract + reopen route; metric semantics fixtures. No live Meta/publisher implementation or invented workbook calculations.
- **Dependencies:** B01/B02; mature audience lesson use B08 consumes result.
- **Acceptance criteria / required behavioral tests / UI acceptance:** Duplicate identical batch,changedcontext/correctedvalue,large stringID,blankvszero,reachvsviews,paidreachvswatchshare,5s/30s duration ratios,lifetimevs72h; UI reopen exact batch→correct match→show prior correction lineage→safecommit.
- **Migration/data compatibility:** Additive import context key/correction metadata; retain rawbytes and legacy observation source; no destructive replace.
- **External prerequisite:** Exact publication mapping; Meta live read lifecycle dependencies remain in TODO stream.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## B17

**Yeterli veri olduğunda gerçek eğitim artifact/registry/inference bağını kur**

- **Priority / journey / effort:** P3; advanced prediction; L/uncertain; no fixed delivery estimate.
- **Observed current behavior:** Production predictions uniformcoldstart,lab empiricalmedian; registry not consulted; train endpointstub. There is no learned artifact pipeline to audit.
- **Expected behavior / root cause:** Dataset source/cutoff/version,stable feature extractor,grouped temporal splits/labels,evaluation,artifacthash,registry-controlled inference,promotion+rollback. Insufficient maturedata stops candidacy honestly.
- **Code/UI evidence and components to reuse:** E26–32; prediction_feature_snapshots/V41,model_versions; existing lab dataset/empirical baseline can serve comparison, not trained claim. Kanıt E kodları [satırlı indekste](audit-evidence/2026-10-08/source-reference-index.md).
- **Minimal change / out-of-scope boundary:** Later statistical model capability; minimal daily-use release excludes it. Retrieval B08 is separate and not weight training.
- **Dependencies:** B13/B16 stable exact observations and sufficiently mature data; B01 sibling lineage.
- **Acceptance criteria / required behavioral tests / UI acceptance:** No outcomes in prerenderfeatures,no futureobservations,no editedsibling train/testsplit,no lifetimeearlylabel,include unsuccessfulrepairs; load artifact prediction featureparity; challenger doesnot change champion;promote changes actual inference;rollback restores artifact.
- **Migration/data compatibility:** Version dataset/feature/artifact contracts; keep historical predictions with immutable originalmodel; migration only when model workflow real.
- **External prerequisite:** Enough verified mature examples,not approximate filename/viewcounts.
- **Definition of done:** Yukarıdaki davranış testleri doğru fixture/ortamda yürütülmüş ve sonuçları kaydedilmiş; tarif edilen UI journey gerçek endpoint/persistence/reopen ile doğrulanmış; hatalar açıklanmış; source/parent IDs, settings/provenance korunmuş. Mock ile live-provider kanıtı ayrı işaretlenmiş; code/build başarısı tek başına Done sayılmamış. Bu maddenin kapsam dışı bileşenleri değiştirilmemiş.

## Release acceptance gate

J1 prompt-only→grounded assessment→save/reopen; J2 boundedrepair→newversion→independentvalidation→bestcandidate; J3 source+actual evidence separate→supported keep/edit/regen; J4 prompt unavailable→no falsefidelity; J5 new parent-linked attempt mockauthorized/blocked→zero deniedcost; J6 crash/retry/reopen without doubledsession/cost; J7 verifiedexample consumed withprovenance and revoked excluded; J8 exactpublication/variant metrics+safe duplicate/correction; J9 directroute preservesIDs and no paidrefresh; J10 missing/unknown/stale/unsupported/timeout/ambiguous controls.

Minimum release live provider kullanmadan mock orchestration+real local file evidence ile değerlendirilebilir. Paid production readiness ayrıca B14 ile doğrulanır. Unknown semantic finding'leri PASS'e çevirmek, placeholdertrain'i trainedmodel diye sunmak veya lessonsave'i retrieval diye isimlendirmek kabul değildir.

İş listesi onay/uygulama talimatını bekler. Audit sırasında özellik, schema, rules, production config veya user content değiştirilmedi.
