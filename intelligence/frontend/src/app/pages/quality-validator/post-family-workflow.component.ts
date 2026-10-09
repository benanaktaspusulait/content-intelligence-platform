import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, EventEmitter, Input, Output, OnChanges, OnDestroy, SimpleChanges, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { GeneralProducibilityComponent } from './general-producibility.component';

@Component({
  selector: 'app-post-family-workflow',
  standalone: true,
  imports: [CommonModule, FormsModule, GeneralProducibilityComponent],
  template: `
  <section class="workflow production-review" aria-label="Production review">
    <header class="review-hero"><div><span class="eyebrow">STEP 4 · PRODUCTION REVIEW</span><h2>Production Review</h2><p>Confirm your creative intent, production settings and references before analysis.</p></div><span class="status-pill" [class.status-pill--ready]="prompt.trim()">{{ prompt.trim() ? 'READY TO REVIEW' : 'MISSING PROMPT' }}</span></header>
    <p *ngIf="restoredRecordId" class="restore-note">Saved review reopened · {{ restoredRecordId }} · no new provider call was made.</p>
    <section class="review-card intent-card"><header><div><span class="card-kicker">CREATIVE INTENT</span><h3>What must be preserved</h3></div><span class="source-badge">{{ protectedIntent ? 'Saved source' : 'Prepared from prompt' }}</span></header><p class="intent-summary">{{ protectedIntent || prompt.slice(0, 420) || 'Creative intent is unavailable until an approved story or saved prompt is selected.' }}</p><div class="intent-actions"><button type="button" class="button button--primary" (click)="confirmIntent()" [disabled]="!prompt.trim()">Confirm intent</button><button type="button" class="button button--secondary" (click)="intentEditing=!intentEditing">{{ intentEditing ? 'Hide intent editor' : 'Edit intent' }}</button><details><summary>View source evidence</summary><p>Source: approved story / saved prompt · version {{ promptVersionId || 'UNKNOWN' }}</p></details></div><textarea *ngIf="intentEditing" [(ngModel)]="protectedIntent" rows="4" placeholder="Edit only when the source-backed creative intent needs correction"></textarea></section>
    <section class="review-card"><header><div><span class="card-kicker">PRODUCTION SETTINGS</span><h3>Inherited workflow settings</h3></div><button type="button" class="button button--secondary" (click)="settingsEditing=!settingsEditing">{{ settingsEditing ? 'Done' : 'Edit settings' }}</button></header><div class="settings-grid"><div><span>Main character</span><strong>{{ characterLabel || 'Unknown' }}</strong><small>{{ characterLabel ? 'Approved catalog / saved source' : 'Missing authoritative character record' }}</small></div><div><span>Content profile</span><strong>{{ contentProfileLabel }}</strong><small>Saved workflow selection</small></div><div><span>Target duration</span><strong>{{ desiredDuration ? desiredDuration + ' seconds' : 'Missing' }}</strong><small>{{ desiredDuration ? 'Inherited from saved production settings' : 'Needs confirmation' }}</small></div><div><span>Aspect ratio</span><strong>{{ aspectRatio || 'Missing' }}</strong><small>{{ aspectRatio ? 'Inherited from saved production settings' : 'Needs confirmation' }}</small></div><div><span>Target generator</span><strong>{{ generatorLabel }}</strong><small>Capability verification remains server-controlled</small></div><div><span>Opening strategy</span><strong>{{ openingStrategyLabel }}</strong><small>System suggestion when available</small></div></div><div *ngIf="settingsEditing" class="settings-editor"><label>Content profile<select [(ngModel)]="contentProfile"><option value="AUTO">Source-based suggestion</option><option value="ABSURD_PHYSICS">Absurd Physics</option><option value="CURIOSITY_ADVENTURE">Curiosity / adventure</option><option value="EDUCATIONAL">Educational</option><option value="MIXED">Mixed</option></select></label><label>Target duration (seconds)<input type="number" min="1" [(ngModel)]="desiredDuration"></label><label>Aspect ratio<select [(ngModel)]="aspectRatio"><option>9:16</option><option>16:9</option><option>1:1</option></select></label><label>Target generator<select [(ngModel)]="generator"><option value="AUTO">System suggestion</option><option value="SEEDANCE_2_0_MINI">Seedance 2.0 Mini</option><option value="SEEDANCE_2_0">Seedance 2.0</option><option value="SEEDANCE_2_5">Seedance 2.5</option></select></label></div></section>
    <section class="review-two-column"><section class="review-card"><header><div><span class="card-kicker">VISUAL REFERENCES</span><h3>Character and first frame</h3></div><span class="status-pill">{{ firstFrameStatus }}</span></header><div class="reference-summary"><div><strong>{{ referenceCharacter || 'Character reference' }}</strong><span>{{ references.length ? references.length + ' validated reference(s)' : 'Approved character reference unavailable' }}</span></div><div><strong>First frame</strong><span>{{ firstFrameStatus }}</span></div></div><button type="button" class="button button--secondary" (click)="referencesOpen=!referencesOpen">{{ referencesOpen ? 'Hide reference details' : 'Manage references' }}</button><div *ngIf="referencesOpen" class="advanced-details"><p *ngFor="let ref of references">{{ ref.character || 'Character' }} · {{ ref.relativePath }}</p><p *ngIf="!references.length">Approved character reference unavailable.</p></div></section><section class="review-card"><header><div><span class="card-kicker">RELEVANT PREVIOUS LESSONS</span><h3>Approved lessons</h3></div><span class="status-pill">{{ retrievedLessons.length ? retrievedLessons.length + ' found' : 'None found' }}</span></header><p>{{ retrievedLessons.length ? 'Applicable verified lessons are attached to this review.' : 'No verified applicable lessons available.' }}</p><details *ngIf="retrievedLessons.length"><summary>View lesson provenance</summary><p *ngFor="let lesson of retrievedLessons">{{ lesson.hypothesis }} · {{ lesson.recordId }}</p></details></section></section>
    <section class="review-card execution-card"><header><div><span class="card-kicker">VISUAL EXECUTION PLAN</span><h3>Source-backed production beats</h3></div><span class="status-pill">{{ review?.productionEvidence?.videoPlanIR?.beats?.length || 0 }} events</span></header><div *ngIf="review?.productionEvidence?.videoPlanIR?.beats?.length; else noBeatEvidence" class="beat-list"><article *ngFor="let beat of review.productionEvidence.videoPlanIR.beats"><strong>{{ beat.startTime != null ? beat.startTime + '–' + beat.endTime + ' s' : 'Sequence position' }}</strong><p>{{ beat.action }}</p><small>{{ beat.sourceQuote || 'Additional evidence required' }}</small></article></div><ng-template #noBeatEvidence><p class="missing-state">No source-backed beat evidence is prepared yet. Analysis may record UNKNOWN where evidence is unavailable.</p></ng-template><details class="advanced-details"><summary>Advanced evidence details</summary><p>Source-bound extraction and raw structured data remain available for diagnostics; ordinary review does not require hand-written JSON.</p><textarea [(ngModel)]="structuredPlanText" rows="3" placeholder="Advanced developer-only evidence editor"></textarea></details></section>
    <section class="review-card readiness-card"><header><div><span class="card-kicker">READINESS</span><h3>Outstanding requirements</h3></div><span class="status-pill" [class.status-pill--ready]="!error">{{ error ? 'NEEDS ATTENTION' : 'READY' }}</span></header><p *ngIf="!error">The exact prompt version and saved source identity are ready for independent quality analysis.</p><p *ngIf="error" class="error">{{ error }}</p><details class="advanced-details"><summary>Validation policy and diagnostics</summary><p>Policy: current approved Family 1–10 contract · workflow profile: {{ profile }} · prompt version: {{ promptVersionId || 'UNKNOWN' }}</p></details><button type="button" class="button button--primary primary-action" (click)="runReview()" [disabled]="busy || !prompt.trim()">{{ busy ? 'Preparing evidence…' : 'Continue to Quality Analysis →' }}</button></section>
    <details class="advanced-details technical-settings"><summary>Advanced details</summary><label>Workflow policy<select [(ngModel)]="profile"><option value="FROZEN">Current approved policy</option><option value="post-family-v1">Operational creative workflow v1</option></select></label><label>Opening strategy<select [(ngModel)]="openingStrategy"><option value="AUTO">System suggestion</option><option value="INSTANT_IMPOSSIBLE">Instant impossibility</option><option value="IMMEDIATE_PROBLEM">Immediate problem</option><option value="CURIOSITY_DISCOVERY">Curiosity / discovery</option></select></label><label>Viewer engagement promise (optional)<input [(ngModel)]="viewerQuestion" placeholder="Optional source-backed question or promise"></label><label>First-frame diagnostics path<input [(ngModel)]="firstFramePath"></label><label>First-frame provider diagnostics<input [(ngModel)]="firstFrameUrl"></label><button type="button" (click)="loadSourceIntent()" [disabled]="busy || !contentId || !promptVersionId">Reload source evidence</button></details>
    <p class="error" *ngIf="error && !readinessCardShown">{{ error }}</p>
  </section>
<ng-container *ngIf="review as r">
        <p class="error" *ngIf="!isCurrent()">
          Prompt, sürüm, referans veya ayar değişti. Bu inceleme eski; yeniden çalıştırın.
        </p>
        <div class="facts" *ngIf="(qa || r).operatorReport as report">
          <p *ngFor="let row of report">
            <strong>{{ row.label }}</strong
            ><br />{{ row.text }}
          </p>
        </div>
        <div class="inputs">
          <article>
            <strong>Prompt / plan kalitesi</strong>
            <p>{{ r.planQuality?.status || 'UNKNOWN' }} · {{ r.planQuality?.recommendation }}</p>
          </article>
          <article>
            <strong>Generator yürütme riski</strong>
            <p>{{ r.executionRisk?.status || 'UNKNOWN' }}</p>
          </article>
          <article>
            <strong>Gerçek render kalitesi</strong>
            <p>
              Plan sadakati: {{ qa?.planFidelity || 'UNKNOWN' }} · Kullanılabilirlik:
              {{ qa?.viewerFacingUsability || 'UNKNOWN' }}
            </p>
          </article>
          <article>
            <strong>İzleyici / dağıtım sonucu</strong>
            <p>{{ measurement ? 'Ölçüm ayrı kayıtta' : 'Henüz ilişkilendirilmedi' }}</p>
          </article>
        </div>
        <a
          [href]="'/api/v1/intelligence/workflow/records/' + (qa?.recordId || r.recordId) + '/pdf'"
          target="_blank"
          >Bu kayıt için PDF raporu</a
        >
        <details>
          <summary>Ham plan, jeneratör ve yetkilendirme kanıtı</summary>
          <div class="facts">
            <p>
              İçerik: <strong>{{ r.routing?.contentProfile }}</strong> · {{ r.routing?.basis }}
            </p>
            <p>
              Açılış: <strong>{{ r.opening?.strategy }}</strong> · Metin planı
              {{ r.opening?.plannedOpening?.status || 'UNKNOWN' }}
            </p>
            <p>
              Suggestionlen / seçilen jeneratör: {{ r.generation?.recommendedGenerator }} /
              {{ r.generation?.selectedGenerator }}
            </p>
            <p>
              İstenen / desteklenen render / edit süresi:
              {{ r.generation?.desiredDuration ?? 'UNKNOWN' }} /
              {{ r.generation?.supportedRenderDuration ?? 'UNKNOWN' }} /
              {{ r.generation?.plannedEditedDuration ?? 'UNKNOWN' }} s
            </p>
            <p>
              Sağlayıcı sözleşmesi: {{ r.generation?.capabilityStatus }} ·
              {{ r.generation?.apiModelId || 'UNKNOWN' }}
            </p>
            <p>
              Creative Quality: {{ r.family8?.creativeQuality?.creativeGrade ?? 'UNKNOWN' }} ·
              Evidence: {{ r.family8?.evidenceCompleteness?.status ?? 'UNKNOWN' }}
            </p>
            <p>
              Render Authorization: <strong>{{ r.family8?.renderAuthorization?.status }}</strong>
            </p>
            <p *ngFor="let reason of r.family8?.renderAuthorization?.reasons">
              {{ reason.message }}
            </p>
          </div>
          <app-general-producibility
            *ngIf="r.generalProducibility?.dimensions"
            [assessment]="r.generalProducibility"
          ></app-general-producibility>
          <h3>Dikkat → ilerleme → yeniden izleme hipotezi</h3>
          <p>{{ r.engagement?.attentionPromise }}</p>
          <p>Son: {{ r.engagement?.endingDelivery }} · {{ r.engagement?.rewatchMechanism }}</p>
          <p>
            İlk kare / gerçek açılış / kapak kanıtı: {{ r.opening?.actualFirstFrame?.status }} /
            {{ r.opening?.actualOpeningVideo?.status }} / {{ r.opening?.cover?.status }}
          </p>
          <p *ngFor="let alternative of r.opening?.alternatives">{{ alternative }}</p>
          <h3>Generator yürütme incelemesi · {{ r.executionReview?.status }}</h3>
          <article *ngFor="let finding of r.executionReview?.findings?.slice(0, 5)">
            <strong
              >{{ finding.riskCategory }} · {{ finding.evidenceBasis }} ·
              {{ finding.confidence }}</strong
            >
            <blockquote>{{ finding.sourceQuote }}</blockquote>
            <p>{{ finding.plausibleFailure }} {{ finding.smallestChange }}</p>
          </article>
          <p>
            Yerel metin eleştirmeni görselleri/klibi incelemiş sayılmaz. DeepSeek ikinci görüşü
            sunucuda yapılandırılabilir; ücretli çağrı varsayılan olarak kapalıdır.
          </p>
        </details>
        <label
          >İkinci görüş sağlayıcısı<select [(ngModel)]="criticProvider">
            <option value="deepseek">DeepSeek · metin portu</option>
            <option value="openai">OpenAI</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
          </select></label
        ><label>Yapılandırılmış eleştirmen modeli<input [(ngModel)]="criticModel" /></label
        ><button
          type="button"
          (click)="secondOpinion()"
          [disabled]="busy || !isCurrent() || !criticModel"
        >
          İkinci görüşü çalıştır
        </button>
        <p *ngIf="opinion">
          İkinci görüş: {{ opinion.secondOpinion?.status }} · kanonik yetkiyi değiştirmez.
        </p>
        <a [href]="renderLink()" *ngIf="r.contentId && r.promptVersionId"
          >Bağlı incelemeyle mevcut render kuyruğunu aç</a
        >
        <details>
          <summary>Kanıt ve belirsizlik</summary>
          <p>Extraction: {{ r.productionEvidence?.videoPlanIR?.metadata?.generalProducibilityEvidence?.extractionVersion || 'UNKNOWN' }} · Source quote coverage: {{ evidenceCoverage(r.productionEvidence) }}. Quote coverage does not establish complete entity or effect tracking.</p>
          <article *ngFor="let claim of r.productionEvidence?.claims">
            <strong>{{ claim.field }} · {{ claim.state }}</strong>
            <blockquote *ngIf="claim.quote">{{ claim.quote }}</blockquote>
            <p>{{ claim.reason }}</p>
            <small>Source {{ claim.sourceId || r.source?.artifact || 'UNKNOWN' }} · version {{ claim.sourceVersion || r.source?.version || 'UNKNOWN' }} · span {{ claim.span?.join('–') || 'UNKNOWN' }} · method {{ claim.methodVersion || 'UNKNOWN' }} · confidence {{ claim.confidence || 'UNKNOWN' }}</small>
          </article>
          <p>Unresolved requirements: {{ r.productionEvidence?.remainingUncertainty?.join(', ') || 'No missing extracted dependency; other unsupported effects may remain UNKNOWN.' }}</p>
          <small>{{ r.source?.sha256 }} · sürüm {{ r.source?.version }}</small>
        </details>
        <h3>Render öncesi temel niyet</h3>
        <p>
          Önem düzeyi bu kaynak sürümüne bağlanır. Değişince yeniden inceleyin; video sonucuna göre
          geriye dönük değiştirilmez.
        </p>
        <article *ngFor="let beat of r.productionEvidence?.videoPlanIR?.beats">
          <p>{{ beat.startTime }}–{{ beat.endTime }} s · {{ beat.action }}</p>
          <button type="button" (click)="setIntentLevel(beat, 'ESSENTIAL')">Temel olay</button>
          <button type="button" (click)="setIntentLevel(beat, 'FLEXIBLE')">Esnek tercih</button>
          <button type="button" (click)="setIntentLevel(beat, 'POLISH')">Görsel incelik</button>
        </article>
        <details>
          <summary>Source-bound intent and creative interpretation details</summary>
          <label
            >Intent requirements<textarea [(ngModel)]="intentRequirementsText"></textarea>
          </label>
          <label
            >Plan notes (source range and rationale)<textarea
              [(ngModel)]="creativeEvidenceText"
            ></textarea>
          </label>
          <p>
            İlerleme bilgi, ilişki, duygu, fizik veya ritimle gelişebilir. Final birden fazla işlev
            taşıyabilir. Kaynaksız yorum UNKNOWN kalır.
          </p>
        </details>
        <details><summary>Bounded repair session · at most two attempts</summary><label>Maximum total cost (USD)<input type="number" min="0" [(ngModel)]="repairBudget"></label><label><input type="checkbox" [(ngModel)]="repairConsent">I approve the configured repair provider within this session budget.</label><button type="button" (click)="startRepairSession()" [disabled]="busy || !isCurrent() || !repairConsent || repairBudget <= 0">Start bounded repair</button><label>Saved session ID<input [(ngModel)]="repairSessionId"></label><button type="button" (click)="reopenRepairSession(repairSessionId)">Reopen session</button><div *ngIf="repairSession"><p>{{ repairSession.sessionId }} · {{ repairSession.state }} · {{ repairSession.stopReason }} · attempts {{ repairSession.attempts }}/{{ repairSession.maxAttempts }} · reserved ceiling {{ repairSession.reservedCostUsd }} (actual spend may be unknown)</p><p>Best independently reviewed prompt version: {{ repairSession.bestPromptVersionId }}</p><section *ngIf="repairOriginalReview && repairBestReview" aria-label="Repair before and after findings"><h4>Original · prompt version {{ repairOriginalReview.promptVersionId }}</h4><pre>{{ repairOriginalReview.executionReview?.findings | json }}</pre><pre>{{ repairOriginalReview.planQuality | json }}</pre><h4>Best independently reviewed candidate · prompt version {{ repairBestReview.promptVersionId }}</h4><pre>{{ repairBestReview.executionReview?.findings | json }}</pre><pre>{{ repairBestReview.planQuality | json }}</pre></section><pre>{{ repairSession.history | json }}</pre><button type="button" (click)="nextRepairAttempt()" [disabled]="busy || repairSession.state !== 'READY'">Next bounded attempt</button><button type="button" (click)="decideRepair('ACCEPTED')" [disabled]="busy || repairSession.state === 'RUNNING'">Accept best candidate</button><button type="button" (click)="decideRepair('REJECTED')">Reject</button><button type="button" (click)="decideRepair('CANCELLED')">Cancel</button></div></details>
        <h3>Minimal repair</h3>
        <label>Source wording to replace<input [(ngModel)]="patchOriginal" /></label
        ><label>Replacement wording<input [(ngModel)]="patchReplacement" /></label>
        <button
          type="button"
          (click)="repair()"
          [disabled]="
            busy || !isCurrent() || !protectedIntent.trim() || !patchOriginal || r.repairPasses > 0
          "
        >
          One patch + final prompt validation
        </button>
        <pre *ngIf="r.diff">{{ r.diff }}</pre>
        <label>Final production prompt<textarea readonly [value]="r.finalPrompt"></textarea></label>
        <button type="button" (click)="copyPrompt()" [disabled]="!isCurrent()">Copy</button>
        <button type="button" (click)="saveFinal.emit(r.finalPrompt)" [disabled]="!isCurrent()">
          Editöre aktar ve sürüm kaydet
        </button>
        <button type="button" (click)="exportHandoff()" [disabled]="!isCurrent()">
          Manuel render paketi indir
        </button>
        <p>
          Manuel paket render yetkisi veya kredi harcama onayı değildir. Son video mevcut kanonik
          kabul akışından geçer.
        </p>
        <h3>Gerçek render QA</h3>
        <label
          >Dönen videonun yerel medya yolu<input
            [(ngModel)]="qaPath"
            placeholder="library/.../video.mp4"
        /></label>
        <p>
          Gerçek klibi açıp her planlanan zaman aralığını inceleyin. Seyrek kareler
          hareket/temas/loop kanıtı değildir.
        </p>
        <a *ngIf="qaPath" [href]="'/api/v1/videos/content?path=' + encode(qaPath)" target="_blank"
          >Gerçek videoyu aç</a
        >
        <article *ngFor="let beat of r.productionEvidence?.videoPlanIR?.beats">
          <strong>{{ beat.startTime }}–{{ beat.endTime }} s</strong>
          <p>{{ beat.action }}</p>
          <label
            >Gerçekte gözlenen başlangıç (s)<input type="number" [(ngModel)]="qaStarts[beat.id]"
          /></label>
          <label
            >Gerçekte gözlenen son (s)<input type="number" [(ngModel)]="qaEnds[beat.id]"
          /></label>
          <select [(ngModel)]="qaStates[beat.id]">
            <option value="UNKNOWN">Kanıt yetersiz</option>
            <option value="PRESENT">Gözlendi</option>
            <option value="ABSENT">Eksik / çöktü</option>
          </select>
        </article>
        <label>İncelenen aralık başlangıcı (s)<input type="number" [(ngModel)]="qaStart" /></label>
        <label>İncelenen aralık sonu (s)<input type="number" [(ngModel)]="qaEnd" /></label>
        <article *ngFor="let aspect of qaAspects">
          <strong>{{ aspect.label }}</strong>
          <select [(ngModel)]="qaExperience[aspect.key]">
            <option value="UNKNOWN">Kanıt yetersiz</option>
            <option *ngFor="let value of aspect.values" [value]="value">{{ value }}</option>
          </select>
          <label
            >Bu aralıkta gerçekten gözlenen şey<input [(ngModel)]="qaDescriptions[aspect.key]"
          /></label>
        </article>
        <details>
          <summary>Aralığa bağlı kusur ve müdahale kanıtı</summary>
          <label>Kusurlar<textarea [(ngModel)]="qaDefectsText"></textarea></label>
          <label>Gerekçeli rerender önerisi<textarea [(ngModel)]="qaRepairText"></textarea></label>
          <p>
            Her kusur için tür, zaman, gözlem, çıkarım/belirsizlik, etkilenen olay/niyet ve izleyici
            etkisi gerekir. Teknik tür tek başına önem düzeyi belirlemez.
          </p>
        </details>
        <label
          ><input type="checkbox" [(ngModel)]="clipReviewed" />Bu aralıkları gerçek klipte inceleyip
          gözlemleri onayladım</label
        >
        <label
          ><input type="checkbox" [(ngModel)]="stillsReviewed" />Bu gerçek videodan çıkarılan
          kareleri inceledim; yalnız durağan görünüm/poz bulguları için kanıt</label
        >
        <button type="button" (click)="runQa()" [disabled]="busy || !isCurrent() || !qaPath">
          Deterministik analiz + plan karşılaştırması
        </button>
        <p *ngIf="qa">ACTUAL_RENDER_QA: {{ qa.status }} · Video {{ qa.videoId }}</p>
        <p *ngFor="let finding of qa?.findings">
          {{ finding.start }}–{{ finding.end }} s · {{ finding.reason }} {{ finding.action }}
        </p>
        <details><summary>Justified full-video regeneration handoff</summary><p>Requires a verified actual review with material full-rerender justification and exact prompt ancestry. Queue authorization and budget controls still apply.</p><label>Parent actual QA record<input [(ngModel)]="regenerationQaId" [placeholder]="qa?.recordId || ''"></label><label>Parent video ID<input [(ngModel)]="regenerationParentVideoId" [placeholder]="qa?.videoId || ''"></label><label>Parent variant ID (optional)<input [(ngModel)]="regenerationParentVariantId"></label><label>Why this new full-video attempt is justified<input [(ngModel)]="regenerationReason"></label><button type="button" (click)="createRegenerationHandoff()" [disabled]="!isCurrent() || !regenerationReason.trim()">Create immutable handoff</button><p *ngIf="regenerationHandoff">{{ regenerationHandoff.status }} · {{ regenerationHandoff.executionScope }}</p><a *ngIf="regenerationHandoff" [href]="regenerationLink()">Review authorized queue settings</a></details>
        <h3>Yayın ve ölçüm ilişkisi</h3>
        <p>
          Prompt → referanslar → render ayarları → gerçek video → edit varyantı → yayın ID →
          immutable ölçüm ayrı tutulur.
        </p>
        <div class="inputs">
          <label
            >Platform<select [(ngModel)]="platform">
              <option>INSTAGRAM</option>
              <option>FACEBOOK</option>
              <option>YOUTUBE</option>
            </select></label
          ><label>Yayın ID (metin)<input type="text" [(ngModel)]="platformContentId" /></label
          ><label>Edit varyant ID (varsa)<input [(ngModel)]="variantId" /></label
          ><label
            >Eşleştirme kanıtı<input
              [(ngModel)]="associationReason"
              placeholder="Doğrulanmış permalink / manuel inceleme gerekçesi"
          /></label>
        </div>
        <button
          type="button"
          (click)="associate()"
          [disabled]="busy || !qa?.videoId || !platformContentId || !associationReason"
        >
          Manuel ilişkiyi kaydet
        </button>
        <p *ngIf="association">
          İlişki: {{ association.status }} · {{ association.platformContentId }}
        </p>
        <a href="/import">CSV/XLSX dosyasını mevcut import ekranında incele ve eşleştir</a>
        <details>
          <summary>Kaynaklı ölçüm kaydı ve karşılaştırma</summary>
          <div class="inputs">
            <label>Ölçüm kaynağı / import satırı<input [(ngModel)]="measurementSource" /></label
            ><label
              >Observation window<select [(ngModel)]="horizon">
                <option>UNKNOWN</option>
                <option>LIFETIME</option>
                <option>1H</option>
                <option>3H</option>
                <option>24H</option>
                <option>72H</option>
              </select></label
            ><label>Ölçüm zamanı<input type="datetime-local" [(ngModel)]="measuredAt" /></label
            ><label
              >Gerçek video süresi (s)<input type="number" [(ngModel)]="videoDuration" /></label
            ><label>Reach<input type="number" [(ngModel)]="reach" /></label
            ><label>Views / plays<input type="number" [(ngModel)]="views" /></label
            ><label>Ortalama izleme (s)<input type="number" [(ngModel)]="watchSeconds" /></label
            ><label>Paid Reach<input type="number" [(ngModel)]="paidReach" /></label
            ><label
              >Paid watch-time payı (0–1)<input type="number" [(ngModel)]="paidWatchShare"
            /></label>
          </div>
          <button
            type="button"
            (click)="saveMeasurement()"
            [disabled]="busy || !association || !measurementSource || !measuredAt"
          >
            Ölçümü ayrı snapshot olarak kaydet
          </button>
          <ng-container *ngIf="measurement"
            ><p>
              Reach {{ measurement.outcome?.reach?.value ?? 'UNKNOWN' }} · Views
              {{ measurement.outcome?.views?.value ?? 'UNKNOWN' }}
            </p>
            <p>
              Ortalama izleme / gerçek süre oranı:
              {{ measurement.audience?.averageWatchDurationRatio?.value ?? 'UNKNOWN' }} ·
              intentional replay oranı değildir.
            </p>
            <p>
              Dağıtım: {{ measurement.distribution?.cohort }} · Paid Reach payı
              {{ measurement.distribution?.paidReachShare?.value ?? 'UNKNOWN' }} · paid watch-time
              payı ayrı.
            </p></ng-container
          >
          <label
            >Near-organic Paid Reach eşiği (0–1)<input
              type="number"
              min="0"
              max="1"
              step="0.01"
              [(ngModel)]="nearOrganicThreshold" /></label
          ><button
            type="button"
            (click)="compare()"
            [disabled]="busy || !['1H', '3H', '24H', '72H'].includes(horizon)"
          >
            Aynı zaman penceresi kohortlarını karşılaştır
          </button>
          <p *ngIf="cohort">
            Dahil {{ cohort.included }} · dışarıda {{ cohort.excluded }} · nedensel sonuç
            çıkarılmaz.
          </p>
        </details>
        <button type="button" (click)="validateCanonicalProfile()" [disabled]="busy || !isCurrent()">Canonical profil doğrulamasını kaydet</button><p *ngIf="canonicalValidationId">{{ canonicalMessage }}</p><details>
          <summary>İnsan incelemesine açık ders / deney kaydı</summary>
          <label>Ders kapsamı<select [(ngModel)]="lessonScope"><option value="ACTUAL_EXECUTION">Doğrulanmış actual video</option><option value="PROMPT_FIX">Kabul edilmiş prompt onarımı</option></select></label><label>Hipotez<textarea [(ngModel)]="lessonHypothesis"></textarea></label
          ><label>Karşı örnekler<input [(ngModel)]="counterexamples" /></label
          ><button
            type="button"
            (click)="saveLesson('LESSON')"
            [disabled]="!lessonHypothesis || (lessonScope === 'PROMPT_FIX' ? repairSession?.state !== 'ACCEPTED' : !qa)"
          >
            Ders adayı kaydet</button
          ><button
            type="button"
            (click)="saveLesson('EXPERIMENT')"
            [disabled]="!lessonHypothesis || (lessonScope === 'PROMPT_FIX' ? repairSession?.state !== 'ACCEPTED' : !qa)"
          >
            Deney sonucu kaydet
          </button>
          <p *ngIf="lesson">{{ lesson.reviewStatus }} · donmuş kurallara otomatik uygulanmaz.</p>
          <ng-container *ngIf="lesson?.reviewStatus === 'PENDING_HUMAN_REVIEW'"
            ><label>İnsan incelemesi gerekçesi<input [(ngModel)]="learningReason" /></label
            ><button type="button" (click)="reviewLesson('APPROVED')" [disabled]="!learningReason">
              Dersi / deneyi onayla</button
            ><button type="button" (click)="reviewLesson('REJECTED')" [disabled]="!learningReason">
              Reddet
            </button></ng-container
          >
          <div *ngIf="lesson?.reviewStatus === 'APPROVED'"><label>Geri çekme gerekçesi<input [(ngModel)]="learningReason"></label><button type="button" (click)="reviewLesson('REVOKED')" [disabled]="!learningReason.trim()">Onaylı dersi geri çek</button></div>
        </details>
      </ng-container>
`,
  styles: [
    `
      .production-review{padding:24px;background:#f7f9fc}.review-hero{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:20px}.review-hero h2{margin:4px 0;font-size:1.7rem;color:#263f56}.review-hero p{margin:0;color:#68747c;font-size:.95rem}.eyebrow,.card-kicker{color:#5f8435;font-size:.7rem;font-weight:800;letter-spacing:.08em}.review-card{display:grid;gap:14px;margin:14px 0;padding:20px;border:1px solid #d8e1ec;border-radius:12px;background:#fff;box-shadow:0 4px 16px rgba(38,63,86,.05)}.review-card header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.review-card h3{margin:3px 0 0;color:#263f56;font-size:1.12rem}.status-pill,.source-badge{display:inline-flex;align-items:center;white-space:nowrap;padding:5px 9px;border-radius:999px;background:#fff5de;color:#855b15;font-size:.67rem;font-weight:800}.status-pill--ready{background:#e8f3dc;color:#31583b}.intent-summary{margin:0;padding:13px;border-left:4px solid #8fbd36;background:#f5faed;color:#40515a;line-height:1.55;white-space:pre-wrap}.intent-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.intent-actions details{padding:0;margin-left:auto}.button{display:inline-flex;align-items:center;justify-content:center;padding:9px 13px;border:1px solid #cbd6ce;border-radius:7px;background:#fff;color:#31583b;font-weight:800;cursor:pointer}.button--primary{background:#31583b;color:#fff;border-color:#31583b}.button:disabled{opacity:.5;cursor:default}.settings-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.settings-grid>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.settings-grid span,.reference-summary span{color:#68747c;font-size:.7rem;font-weight:800;text-transform:uppercase}.settings-grid strong{font-size:.95rem;color:#263f56}.settings-grid small{color:#68747c;font-size:.72rem}.settings-editor{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding-top:8px;border-top:1px solid #e4e9e5}.review-two-column{display:grid;grid-template-columns:1fr 1fr;gap:14px}.review-two-column .review-card{margin:0}.reference-summary{display:grid;grid-template-columns:1fr 1fr;gap:12px}.reference-summary>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px}.reference-summary strong{color:#263f56}.beat-list{display:grid;gap:9px}.beat-list article{display:grid;gap:4px;margin:0;padding:12px;border:1px solid #dfe7ee;border-radius:8px;background:#fbfcfd}.beat-list article strong{color:#31583b}.beat-list article p,.beat-list article small{margin:0;color:#40515a}.missing-state{margin:0;padding:14px;background:#fff9ed;border:1px solid #ecd2a2;border-radius:8px;color:#855b15}.advanced-details{color:#52616b}.advanced-details summary{cursor:pointer;font-weight:800}.readiness-card{border-color:#cbded0}.primary-action{justify-self:start}.restore-note{padding:10px 12px;border-radius:7px;background:#edf5fb;color:#40515a}.technical-settings{margin-top:16px;padding:12px 0}.technical-settings label{max-width:420px}.error{color:#983520}@media(max-width:900px){.settings-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.settings-editor{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.production-review{padding:14px}.review-hero{display:grid}.review-two-column,.settings-grid,.settings-editor,.reference-summary{grid-template-columns:1fr}.review-card{padding:15px}.intent-actions details{margin-left:0}.primary-action{width:100%}}
      .workflow {
        border: 1px solid #ccd7e4;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        background: #f7f9fc;
        color: #20334a;
      }
      .inputs {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
      }
      label {
        display: block;
        margin: 10px 0;
      }
      input,
      select,
      textarea {
        display: block;
        max-width: 100%;
        width: 100%;
        padding: 8px;
        border: 1px solid #b8c5d5;
        border-radius: 6px;
      }
      input[type='checkbox'] {
        display: inline;
        width: auto;
      }
      textarea {
        min-height: 85px;
      }
      button {
        margin: 8px 8px 8px 0;
        padding: 8px 12px;
        cursor: pointer;
      }
      button:disabled {
        opacity: 0.5;
        cursor: default;
      }
      article {
        border-top: 1px solid #d4dce8;
        padding: 10px 0;
      }
      details {
        padding: 12px 0;
      }
      .error {
        color: #983520;
      }
      pre,
      small {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }
      .facts {
        background: white;
        padding: 12px;
        margin: 12px 0;
      }
    `,
  ],
})
export class PostFamilyWorkflowComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private changeDetector = inject(ChangeDetectorRef);
  @Input() prompt = '';
  @Input() contentId = '';
  @Input() promptVersionId = '';
  @Input() sourcePath = '';
  @Input() videoPath = '';
  @Input() workflowProfile = 'FROZEN';
  @Output() saveFinal = new EventEmitter<string>();
  @Output() acceptedVersion = new EventEmitter<{contentId: number; promptVersionId: number; rawText: string; repairSessionId: string}>();
  intentEditing = false; settingsEditing = false; referencesOpen = false; intentConfirmed = false; readinessCardShown = true;
  profile = 'FROZEN';
  contentProfile = 'AUTO';
  get contentProfileLabel():string{return this.contentProfile === 'AUTO' ? 'Source-based suggestion' : this.contentProfile.replaceAll('_',' ');}
  get generatorLabel():string{return this.generator === 'AUTO' ? 'System suggestion' : this.generator.replaceAll('_',' ');}
  get openingStrategyLabel():string{return this.openingStrategy === 'AUTO' ? 'System suggestion' : this.openingStrategy.replaceAll('_',' ');}
  get characterLabel():string{return this.referenceCharacter || (this.references[0]?.character || 'Unknown');}
  get firstFrameStatus():string{return this.firstFramePath || this.firstFrameUrl ? 'Needs validation' : 'Not yet available';}
  confirmIntent(){this.intentConfirmed=true;this.intentRequirementsText=JSON.stringify(this.protectedIntent.split('\n').map(value=>value.trim()).filter(Boolean));this.changeDetector.markForCheck();}

  openingStrategy = 'AUTO';
  generator = 'AUTO';
  desiredDuration: number | null = null;
  qualityJustification = '';
  aspectRatio = '';
  structuredPlanText = '';
  intentRequirementsText = '[]';
  creativeEvidenceText = '[]';
  intentChangeReason = '';
  qaDefectsText = '[]';
  qaRepairText = '{}';
  qaStart = 0;
  qaEnd: number | null = null;
  qaExperience: Record<string, string> = {};
  qaDescriptions: Record<string, string> = {};
  qaAspects = [
    {
      key: 'coreEventReadability',
      label: 'Temel olayın okunabilirliği',
      values: ['ADEQUATE', 'UNREADABLE'],
    },
    { key: 'identity', label: 'Kimlik', values: ['RECOGNIZABLE', 'UNRECOGNIZABLE'] },
    {
      key: 'safety',
      label: 'Çocukla paylaşım için içerik güvenliği',
      values: ['APPROPRIATE', 'UNSAFE'],
    },
    { key: 'coherence', label: 'Bütün olarak anlaşılabilirlik', values: ['ADEQUATE', 'DESTROYED'] },
    {
      key: 'progression',
      label: 'İzleme deneyiminin gelişimi',
      values: ['DEVELOPING', 'PURPOSEFUL_REPETITION', 'WEAK'],
    },
    {
      key: 'opening',
      label: 'Gerçek açılış',
      values: [
        'READABLE_EARLY_DEVELOPMENT',
        'READABLE_PROMISE',
        'UNREADABLE',
        'EXCESSIVELY_DELAYED',
      ],
    },
    {
      key: 'ending',
      label: 'Gerçek final',
      values: ['DELIVERS_PROMISE', 'PURPOSEFUL_UNRESOLVED', 'ARBITRARY_TRUNCATION', 'WEAK'],
    },
  ];
  plannedEditedDuration: number | null = null;
  viewerQuestion = '';
  evidenceCoverage(evidence: any): string {
    const total = Array.from(this.prompt).length;
    if (!total) return 'UNKNOWN';
    const intervals: number[][] = (evidence?.claims || []).map((claim: any) => claim.span)
      .filter((span: any) => Array.isArray(span) && span.length === 2 && Number.isInteger(span[0]) && Number.isInteger(span[1]) && span[0] >= 0 && span[1] > span[0] && span[1] <= total)
      .sort((a: number[], b: number[]) => a[0] - b[0]);
    let count = 0, end = 0;
    for (const span of intervals) { count += Math.max(0, span[1] - Math.max(end, span[0])); end = Math.max(end, span[1]); }
    return `${count}/${total} Unicode characters (${Math.round(100 * count / total)}%)`;
  }

  protectedIntent = '';
  firstFramePath = '';
  firstFrameUrl = '';
  referenceCharacter = '';
  referencePath = '';
  references: Array<{ character: string; relativePath: string; kind: string }> = [];
  review: any = null;
  busy = false;
  error = '';
  private reviewedInputs = '';
  patchOriginal = '';
  patchReplacement = '';
  qaPath = '';
  qaStates: Record<string, string> = {};
  qaStarts: Record<string, number> = {};
  qaEnds: Record<string, number> = {};
  clipReviewed = false;
  stillsReviewed = false;
  qa: any = null;
  platform = 'INSTAGRAM';
  platformContentId = '';
  variantId = '';
  associationReason = '';
  association: any = null;
  measurementSource = '';
  horizon = 'UNKNOWN';
  measuredAt = '';
  videoDuration: number | null = null;
  reach: number | null = null;
  views: number | null = null;
  watchSeconds: number | null = null;
  paidReach: number | null = null;
  paidWatchShare: number | null = null;
  measurement: any = null;
  cohort: any = null;
  criticProvider = 'deepseek';
  criticModel = '';
  opinion: any = null;
  nearOrganicThreshold = 0.05;
  learningReason = '';
  lessonModelVersion = '';
  retrievedLessons: any[] = [];
  retrieveLessons() {
    this.http.get<any[]>('/api/v1/intelligence/workflow/learning/retrieve', { params: { contentProfile: this.contentProfile, modelVersion: this.lessonModelVersion, duration: this.desiredDuration || 0, generator:this.generator, settings:JSON.stringify(this.options().settings) } }).subscribe({ next: lessons => { this.retrievedLessons = lessons; this.changeDetector.markForCheck(); }, error: e => this.fail(e) });
  }
  lessonHypothesis = '';
  lessonScope = 'ACTUAL_EXECUTION';
  counterexamples = '';
  lesson: any = null;
  encode = encodeURIComponent;
  regenerationQaId = '';
  regenerationParentVideoId = '';
  regenerationParentVariantId = '';
  regenerationReason = '';
  regenerationHandoff: any = null;
  createRegenerationHandoff() {
    if (!this.isCurrent() || !this.regenerationReason.trim()) return;
    this.http.post<any>('/api/v1/intelligence/workflow/regeneration-handoff', { qaRecordId: this.regenerationQaId || this.qa?.recordId, reviewId: this.review.recordId, parentVideoId: this.regenerationParentVideoId || this.qa?.videoId, parentVariantId: this.regenerationParentVariantId || null, reason: this.regenerationReason.trim() }).subscribe({ next: handoff => { this.regenerationHandoff = handoff; this.changeDetector.markForCheck(); }, error: e => this.fail(e) });
  }
  regenerationLink() {
    return '/render?' + new URLSearchParams({ contentId: String(this.regenerationHandoff.contentId), promptVersionId: String(this.regenerationHandoff.promptVersionId), workflowReviewId: this.regenerationHandoff.reviewId, regenerationHandoffId: this.regenerationHandoff.recordId }).toString();
  }
  repairBudget = 0;
  repairConsent = false;
  repairSession: any = null;
  repairOriginalReview: any = null;
  repairBestReview: any = null;
  private repairKey = '';
  private autoRepair = false;
  private repairOperation = 0;
  startRepairSession() {
    if (!this.isCurrent() || !this.repairConsent || this.repairBudget <= 0 || this.busy) return;
    this.busy = true;
    this.autoRepair = true;
    this.repairOriginalReview = null; this.repairBestReview = null;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    this.repairKey ||= crypto.randomUUID();
    this.http.post<any>('/api/v1/intelligence/workflow/repair-sessions', { reviewId: this.review.recordId, idempotencyKey: this.repairKey, maxAttempts: 2, maxCostUsd: this.repairBudget }).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation) return;
      this.repairSession = session; this.repairSessionId = session.sessionId; this.busy = false;
      const url = new URL(window.location.href); url.searchParams.set('repairSessionId', session.sessionId); window.history.replaceState(window.history.state, '', url.toString());
      this.nextRepairAttempt(true); }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation) { this.autoRepair = false; this.fail(e); } } });
  }
  nextRepairAttempt(continueAutomatically = false) {
    if (this.repairSession?.state !== 'READY' || this.busy) return;
    if (this.repairSession.attempts >= Math.min(this.repairSession.maxAttempts, 2)) return;
    const sequence = this.restoreSequence;
    const operation = this.repairOperation;
    const sessionId = this.repairSession.sessionId;
    const previousAttempts = this.repairSession.attempts;
    this.busy = true;
    this.http.post<any>(`/api/v1/intelligence/workflow/repair-sessions/${sessionId}/step`, {}).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== sessionId) return;
      this.repairSession = session; this.busy = false; this.changeDetector.markForCheck();
      if (continueAutomatically && this.autoRepair && session.state === 'READY'
          && session.stopReason === 'NEXT_ATTEMPT_AVAILABLE' && session.attempts > previousAttempts
          && session.history?.at(-1)?.stage === 'INDEPENDENTLY_REVIEWED') this.nextRepairAttempt(true);
      else { this.autoRepair = false; this.loadRepairComparison(session); }
    }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation && this.repairSession?.sessionId === sessionId) { this.autoRepair = false; this.fail(e); } } });
  }
  decideRepair(decision: string) {
    if (!this.repairSession) return;
    this.autoRepair = false;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    const sessionId = this.repairSession.sessionId;
    this.http.post<any>(`/api/v1/intelligence/workflow/repair-sessions/${this.repairSession.sessionId}/decision`, { decision }).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== sessionId) return;
      this.repairSession = session;
      this.busy = false;
      if (session.state === 'ACCEPTED') this.http.get<any>(`/api/v1/intelligence/workflow/records/${session.bestReviewId}`).subscribe({ next: review => { if (sequence === this.restoreSequence && this.repairSession?.sessionId === sessionId) this.acceptedVersion.emit({ contentId: session.contentId, promptVersionId: session.bestPromptVersionId, rawText: review.originalPrompt, repairSessionId: session.sessionId }); }, error: e => { if (sequence === this.restoreSequence) this.fail(e); } });
      this.changeDetector.markForCheck();
    }, error: e => this.fail(e) });
  }
  reopenRepairSession(id: string) {
    if (!id.trim()) return;
    this.autoRepair = false;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    this.http.get<any>(`/api/v1/intelligence/workflow/repair-sessions/${encodeURIComponent(id.trim())}`).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation) return;
      if (String(session.contentId) !== this.contentId || ![String(session.originalPromptVersionId), String(session.bestPromptVersionId)].includes(this.promptVersionId)) { this.error = 'Repair session belongs to another source version.'; return; }
      this.repairSession = session; this.repairSessionId = session.sessionId; this.loadRepairComparison(session); this.changeDetector.markForCheck();
    }, error: e => this.fail(e) });
  }
  ngOnDestroy(): void { this.autoRepair = false; this.repairOperation++; this.restoreSequence++; }
  private loadRepairComparison(session: any): void {
    if (!session.originalReviewId || !session.bestReviewId) return;
    const sequence = this.restoreSequence, operation = this.repairOperation;
    for (const [field, id] of [['repairOriginalReview', session.originalReviewId], ['repairBestReview', session.bestReviewId]] as const) {
      this.http.get<any>(`/api/v1/intelligence/workflow/records/${id}`).subscribe({ next: review => {
        if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== session.sessionId) return;
        this[field] = review; this.changeDetector.markForCheck();
      }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation) this.fail(e); } });
    }
  }
  repairSessionId = '';
  restoredRecordId = '';
  private restoreSequence = 0;
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['workflowProfile']) this.profile = changes['workflowProfile'].currentValue || 'FROZEN';
    if (!changes['contentId'] && !changes['promptVersionId'] && !changes['workflowProfile']) return;
    this.review = null;
    this.qa = null;
    this.repairKey = '';
    this.autoRepair = false;
    this.repairOperation++;
    this.repairSession = null;
    this.repairOriginalReview = null;
    this.repairBestReview = null;
    this.busy = false;
    this.repairConsent = false;
    this.repairBudget = 0;
    this.reviewedInputs = '';
    this.restoredRecordId = '';
    this.hydrateSettingsFromPrompt();
    const sequence = ++this.restoreSequence;
    if (!this.contentId || !this.promptVersionId) return;
    const savedSessionId = new URL(window.location.href).searchParams.get('repairSessionId');
    if (savedSessionId) this.reopenRepairSession(savedSessionId);
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=REVIEW', { params: { contentId: this.contentId, promptVersionId: this.promptVersionId } }).subscribe({
      next: rows => {
        if (sequence !== this.restoreSequence) return;
        const saved = rows.find(row => String(row.contentId) === this.contentId && String(row.promptVersionId) === this.promptVersionId);
        if (!saved) return;
        this.review = saved;
        this.restoredRecordId = saved.recordId;
        this.profile = 'post-family-v1';
        const bound = saved.boundRequest || {};
        this.canonicalValidationId = bound.canonicalValidationId || bound.authorizationEvidence?.validationRecordId || null;
        for (const key of ['contentProfile', 'openingStrategy', 'generator', 'desiredDuration', 'qualityJustification', 'viewerQuestion', 'plannedEditedDuration', 'intentChangeReason', 'lessonModelVersion'] as const) {
          if (bound[key] !== undefined) (this as any)[key] = bound[key];
        }
        this.intentRequirementsText = JSON.stringify(bound.intentRequirements || [], null, 2);
        this.creativeEvidenceText = JSON.stringify(bound.creativeEvidence || [], null, 2);
        this.protectedIntent = (bound.protectedIntent || []).join('\n');
        this.structuredPlanText = bound.structuredPlan ? JSON.stringify(bound.structuredPlan, null, 2) : '';
        this.references = (bound.references || []).filter((ref: any) => ref.kind !== 'FIRST_FRAME');
        const frame = (bound.references || []).find((ref: any) => ref.kind === 'FIRST_FRAME');
        this.firstFramePath = frame?.relativePath || '';
        this.firstFrameUrl = bound.settings?.startFrame?.url || '';
        this.aspectRatio = bound.settings?.aspectRatio || '9:16';
        this.qaPath = this.videoPath;
        if (saved.decisionPolicyVersion === 'impact-review-v1' && bound.prompt === this.prompt) {
          this.reviewedInputs = this.inputSnapshot();
        } else this.error = 'Tarihsel inceleme: kaynak veya karar politikası değişmiş; yeni değerlendirme gerekli.';
        this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA', { params: { bindingHash: saved.bindingHash } }).subscribe({
          next: records => {
            if (sequence !== this.restoreSequence) return;
            this.qa = records.find(row => row.bindingHash === saved.bindingHash) || null;
            this.changeDetector.markForCheck();
          }, error: e => this.fail(e),
        });
        this.changeDetector.markForCheck();
      }, error: e => this.fail(e),
    });
  }

  private hydrateSettingsFromPrompt(){const text=this.prompt||'';const duration=text.match(/(?:duration|target duration|length)\s*[:=]?\s*(\d{1,2})\s*(?:s|sec|seconds)?/i)||text.match(/\b(5|8|10|12|15|20|25|30)\s*(?:s|sec|seconds)\b/i);if(!this.desiredDuration&&duration)this.desiredDuration=Number(duration[1]);const ratio=text.match(/\b(9:16|16:9|1:1)\b/);if(!this.aspectRatio&&ratio)this.aspectRatio=ratio[1];}
  private options() {
    return {
      profile: this.profile,
      canonicalValidationId: this.canonicalValidationId,
      lessonModelVersion: this.lessonModelVersion,
      contentProfile: this.contentProfile,
      openingStrategy: this.openingStrategy,
      generator: this.generator,
      desiredDuration: this.desiredDuration,
      qualityJustification: this.qualityJustification,
      viewerQuestion: this.viewerQuestion,
      plannedEditedDuration: this.plannedEditedDuration,
      structuredPlan: this.parsedPlan(),
      intentRequirements: this.parseList(this.intentRequirementsText),
      creativeEvidence: this.parseList(this.creativeEvidenceText),
      intentChangeReason: this.intentChangeReason,
      protectedIntent: this.protectedIntent
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
      references: this.firstFramePath
        ? [
            ...this.references,
            { character: '', kind: 'FIRST_FRAME', relativePath: this.firstFramePath },
          ]
        : this.references,
      settings: {
        mode: 'image2video',
        aspectRatio: this.aspectRatio,
        resolution: '480p',
        ...(this.firstFramePath
          ? {
              startFrame: {
                type: 'image',
                id: this.firstFramePath,
                url: this.firstFrameUrl,
                label: 'Reviewed first frame',
              },
            }
          : {}),
      },
      segments: [],
    };
  }
  loadSourceIntent() {
    this.busy = true;
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=REVIEW', { params: { contentId: this.contentId, promptVersionId: this.promptVersionId } }).subscribe({
      next: (rows) => {
        const source = rows.find(
          (r) =>
            String(r.contentId) === this.contentId &&
            String(r.promptVersionId) === this.promptVersionId &&
            r.decisionPolicyVersion === 'impact-review-v1',
        );
        if (source) {
          this.intentRequirementsText = JSON.stringify(
            source.boundRequest?.intentRequirements || [],
            null,
            2,
          );
          this.creativeEvidenceText = JSON.stringify(
            source.boundRequest?.creativeEvidence || [],
            null,
            2,
          );
          this.protectedIntent = (source.boundRequest?.protectedIntent || []).join('\n');
          this.error = '';
        } else this.error = 'Bu kaynak sürümüne ait etki incelemesi bulunamadı.';
        this.busy = false;
        this.changeDetector.markForCheck();
      },
      error: (e) => this.fail(e),
    });
  }
  private parseList(text: string) {
    try {
      const value = JSON.parse(text);
      return Array.isArray(value) ? value : null;
    } catch {
      return null;
    }
  }
  setIntentLevel(beat: any, level: string) {
    const items = this.parseList(this.intentRequirementsText) || [];
    const quote = Array.from(this.prompt).slice(beat.sourceSpan[0], beat.sourceSpan[1]).join('');
    this.intentRequirementsText = JSON.stringify(
      [
        ...items.filter((i: any) => i.id !== beat.id),
        {
          id: beat.id,
          level,
          sourceSpan: beat.sourceSpan,
          sourceQuote: quote,
          eventIds: [beat.id],
          rationale: 'Operatörün render öncesi kaynak olay tercihi',
        },
      ],
      null,
      2,
    );
  }
  private parsedPlan() {
    try {
      return this.structuredPlanText.trim() ? JSON.parse(this.structuredPlanText) : null;
    } catch {
      return null;
    }
  }
  private inputSnapshot() {
    return JSON.stringify({
      structuredPlanText: this.structuredPlanText,
      prompt: this.prompt,
      contentId: this.contentId,
      promptVersionId: this.promptVersionId,
      options: this.options(),
    });
  }
  isCurrent() {
    return !!this.review && this.inputSnapshot() === this.reviewedInputs;
  }
  addReference() {
    this.references = [
      ...this.references,
      {
        character: this.referenceCharacter,
        relativePath: this.referencePath,
        kind: 'CHARACTER_REFERENCE',
      },
    ];
    this.referencePath = '';
  }
  runReview() {
    if (this.profile !== 'post-family-v1') return;
    if (this.structuredPlanText.trim() && !this.parsedPlan()) {
      this.error = 'Kaynağa bağlı plan JSON olarak okunamadı; kaynak kanıtı güncellenmedi.';
      return;
    }
    if (
      !this.parseList(this.intentRequirementsText) ||
      !this.parseList(this.creativeEvidenceText)
    ) {
      this.error = 'Niyet/yorum bildirimleri okunamadı; kaynak incelemesi yapılmadı.';
      return;
    }
    this.busy = true;
    this.error = '';
    const snapshot = this.inputSnapshot();
    this.http
      .post<any>('/api/v1/intelligence/workflow/review', {
        contentId: Number(this.contentId) || null,
        promptVersionId: Number(this.promptVersionId) || null,
        prompt: this.prompt,
        sourcePath: this.sourcePath,
        options: this.options(),
      })
      .subscribe({
        next: (r) => {
          this.review = r;
          this.reviewedInputs = r.originalPrompt !== undefined && r.originalPrompt !== this.prompt ? '' : snapshot;
          if (!this.reviewedInputs) this.error = 'Düzenlenen metni yeni immutable sürüm olarak kaydedin; sunucu kayıtlı kaynak sürümünü inceledi.';
          this.busy = false;
          this.changeDetector.markForCheck();
          this.qaPath = this.videoPath;
          this.qaStates = {};
          this.qaStarts = {};
          this.qaEnds = {};
          this.qaExperience = {};
          this.qaDescriptions = {};
          this.qaEnd = null;
          this.clipReviewed = false;
          this.stillsReviewed = false;
          this.qa = null;
          this.association = null;
        },
        error: (e) => this.fail(e),
      });
  }
  repair() {
    const start = this.prompt.indexOf(this.patchOriginal);
    if (start < 0 || this.prompt.indexOf(this.patchOriginal, start + 1) >= 0) {
      this.error = 'Yama ifadesi kaynakta tam bir kez bulunmalı.';
      return;
    }
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/repair`, {
        patches: [
          {
            start: Array.from(this.prompt.slice(0, start)).length,
            end: Array.from(this.prompt.slice(0, start + this.patchOriginal.length)).length,
            sourceQuote: this.patchOriginal,
            replacement: this.patchReplacement,
          },
        ],
      })
      .subscribe({
        next: (r) => {
          this.review = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  async copyPrompt() {
    await navigator.clipboard.writeText(this.review.finalPrompt);
  }
  exportHandoff() {
    const blob = new Blob([JSON.stringify(this.review, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pompom-manual-render-review.json';
    a.click();
    URL.revokeObjectURL(url);
  }
  runQa() {
    const defects = this.parseList(this.qaDefectsText);
    let repairProposal: any;
    try {
      repairProposal = JSON.parse(this.qaRepairText);
    } catch {
      this.error = 'Müdahale kanıtı okunamadı';
      return;
    }
    if (!defects || !repairProposal || Array.isArray(repairProposal)) {
      this.error = 'Kusur/müdahale kanıtı okunamadı';
      return;
    }
    this.busy = true;
    const beats = this.review.productionEvidence.videoPlanIR.beats;
    const duration = Math.max(...beats.map((b: any) => b.endTime), 0);
    const end = this.qaEnd ?? this.videoDuration ?? duration;
    const events = beats.map((b: any) => ({
      id: b.id,
      start: this.qaStarts[b.id] ?? (this.qaStates[b.id] === 'ABSENT' ? this.qaStart : b.startTime),
      end: this.qaEnds[b.id] ?? (this.qaStates[b.id] === 'ABSENT' ? end : b.endTime),
      state: this.qaStates[b.id] || 'UNKNOWN',
      evidenceBasis: this.clipReviewed ? 'HUMAN_REVIEWED_CLIP' : 'SAMPLED_STILLS',
      reference: `${this.qaPath}#t=${this.qaStarts[b.id] ?? b.startTime},${this.qaEnds[b.id] ?? b.endTime}`,
      observed:
        this.qaStates[b.id] === 'PRESENT'
          ? 'Operatör bu plan olayını gerçek klip aralığında gözledi.'
          : this.qaStates[b.id] === 'ABSENT'
            ? 'Operatör bu plan olayının gerçek klip aralığında bulunmadığını gözledi.'
            : '',
      inferred: '',
      uncertainty: 'Operatör gözlemi; otomatik semantik doğrulama yapılmadı',
      confidence: this.clipReviewed ? 'MEDIUM' : 'UNKNOWN',
    }));
    const experience = Object.fromEntries(
      this.qaAspects.map((a) => [
        a.key,
        {
          value: this.qaExperience[a.key] || 'UNKNOWN',
          start: this.qaStart,
          end,
          observed: this.qaDescriptions[a.key] || '',
          inferred: '',
          uncertainty: 'Operatör gözlemi; ses/transkript kanıtı yok',
          confidence: this.clipReviewed ? 'MEDIUM' : 'UNKNOWN',
          evidenceBasis: this.clipReviewed ? 'HUMAN_REVIEWED_CLIP' : 'SAMPLED_STILLS',
          reference: `${this.qaPath}#t=${this.qaStart},${end}`,
        },
      ]),
    );
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/qa`, {
        relativePath: this.qaPath,
        humanReviewed: this.clipReviewed,
        stillsReviewed: this.stillsReviewed,
        observation: { coverage: [this.qaStart, end], events, experience, defects, repairProposal },
      })
      .subscribe({
        next: (r) => {
          this.qa = r;
          this.busy = false;
          this.changeDetector.markForCheck();
          this.videoDuration = r.technicalAnalysis?.metadata?.durationMs / 1000 || null;
        },
        error: (e) => this.fail(e),
      });
  }
  associate() {
    this.busy = true;
    this.http
      .post<any>('/api/v1/intelligence/workflow/feedback/ASSOCIATION', {
        platform: this.platform,
        platformContentId: this.platformContentId,
        videoId: this.qa.videoId,
        variantId: this.variantId || null,
        reviewId: this.review.recordId,
        qaRecordId: this.qa.recordId,
        renderAttemptId: null,
        reviewReason: this.associationReason,
      })
      .subscribe({
        next: (r) => {
          this.association = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  saveMeasurement() {
    this.busy = true;
    this.http
      .post<any>('/api/v1/intelligence/workflow/feedback/MEASUREMENT', {
        observation: {
          associationRecordId: this.association.recordId,
          platform: this.platform,
          platformContentId: this.platformContentId,
          sourceId: this.measurementSource,
          window: this.horizon,
          observedAt: new Date(this.measuredAt).toISOString(),
          durationSeconds: this.videoDuration,
          reach: this.reach,
          views: this.views,
          averageWatchSeconds: this.watchSeconds,
          paidReach: this.paidReach,
          paidWatchTimeShare: this.paidWatchShare,
        },
      })
      .subscribe({
        next: (r) => {
          this.measurement = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  compare() {
    this.busy = true;
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=MEASUREMENT').subscribe({
      next: (records) =>
        this.http
          .post<any>('/api/v1/intelligence/workflow/feedback/COHORT', {
            records: records.map((r) => r.raw),
            horizon: this.horizon,
            nearOrganicThreshold: this.nearOrganicThreshold,
          })
          .subscribe({
            next: (r) => {
              this.cohort = r;
              this.busy = false;
              this.changeDetector.markForCheck();
            },
            error: (e) => this.fail(e),
          }),
      error: (e) => this.fail(e),
    });
  }
  canonicalValidationId: number | null = null;
  canonicalMessage = ''; 
  validateCanonicalProfile() {
    if(!this.review?.recordId || !this.isCurrent()) return;
    this.busy=true;
    this.http.post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/canonical-validation`,{}).subscribe({
      next: value => {this.canonicalValidationId=value.validationRecordId; this.busy=false; this.canonicalMessage=`Canonical profile validation #${this.canonicalValidationId}: ${value.report?.status || 'recorded'}. Visual gates and independent revalidation remain required. Review again to bind the new canonical evidence.`;this.changeDetector.markForCheck();},
      error: response => {this.busy=false;this.error=response.error?.message || 'Canonical profile validation failed';this.changeDetector.markForCheck();}
    });
  }

  saveLesson(kind: string) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/learning/${kind}`, {
        hypothesis: this.lessonHypothesis,
        lessonScope: this.lessonScope,
        evidenceBasis: this.lessonScope === 'PROMPT_FIX' ? [this.repairSession?.history?.find((attempt: any) => attempt.reviewId === this.repairSession.bestReviewId)?.repairRecordId].filter(Boolean) : [this.qa?.recordId].filter(Boolean),
        sampleSize: 1,
        targetModelVersion: this.review.generation.profileVersion,
        settings: this.review.generation.settings,
        contentProfile: this.review.routing.contentProfile,
        durationRange: [this.lessonScope === 'PROMPT_FIX' ? this.desiredDuration : this.videoDuration, this.lessonScope === 'PROMPT_FIX' ? this.desiredDuration : this.videoDuration],
        observedResult: this.lessonScope === 'PROMPT_FIX' ? this.review?.executionReview?.status || 'UNKNOWN' : this.qa?.viewerFacingUsability || 'UNKNOWN',
        counterexamples: this.counterexamples,
      })
      .subscribe({
        next: (r) => {
          this.lesson = r;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  secondOpinion() {
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/critic`, {
        provider: this.criticProvider,
        model: this.criticModel,
      })
      .subscribe({
        next: (r) => {
          this.opinion = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  renderLink() {
    return (
      '/render?' +
      new URLSearchParams({
        contentId: String(this.review?.contentId || ''),
        promptVersionId: String(this.review?.promptVersionId || ''),
        workflowReviewId: this.review?.recordId || '',
      }).toString()
    );
  }
  reviewLesson(decision: string) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.lesson.recordId}/learning-review`, {
        decision,
        reason: this.learningReason,
      })
      .subscribe({
        next: (r) => {
          this.lesson = r;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  private fail(error: any) {
    this.busy = false;
    this.changeDetector.markForCheck();
    this.error =
      error.error?.detail ||
      error.error?.message ||
      'İşlem tamamlanamadı; kanıt UNKNOWN olarak kalır.';
  }
}
