import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subject, firstValueFrom, takeUntil } from 'rxjs';
interface OpenArtReferenceAsset {
  id: string;
  canonicalKey: string;
  displayName: string;
  source: 'LOCAL' | 'OPENART_WORKSPACE';
  mediaType: string;
  providerAssetId?: string;
  providerUrl?: string;
  localPath?: string;
  sha256?: string;
  status: string;
}

interface OpenArtCapabilities {
  imageMultipleReferences: string;
  videoSingleStartFrame: string;
  videoMultipleElementReferences: string;
  workspaceAssetDiscovery: string;
}

interface VisualReferencePlan {
  planId: string;
  renderJobId?: string;
  contentId?: number;
  promptVersionNumber?: number;
  promptVersionId: number;
  promptSha256: string;
  promptReady: boolean;
  firstFrameStatus: string;
  firstFrameCandidates: Array<{
    assetId: string;
    role: string;
    source: string;
    relativePath: string;
    sha256: string;
    promptVersionMatches: boolean;
    mediaVerified: boolean;
    eligible?: boolean;
    quarantined?: boolean;
    semanticStatus: string;
  }>;
  referenceBindings?: Array<{
    assetId: string;
    role: string;
    sourceKind: string;
    relativePath: string;
    sha256: string;
    validationStatus: string;
    accepted: boolean;
    evidence?: any;
    mediaUrl?: string;
  }>;
  recommendation: {
    strategy: string;
    action: string;
    criticalScene: string;
    reason: string;
    additionalReferenceSupport: string;
  };
  capabilities: OpenArtCapabilities;
  modelCapabilities?: {
    model: string;
    startFrame: string;
    endFrame: string;
    multipleVideoReferences: string;
    intermediateKeyframe: string;
    segmentContinuation: string;
    verificationSource: string;
  };
  generationProposal?: {
    promptText: string;
    model: string;
    referenceRoles: string[];
    aspectRatio: string;
    dimensions: string;
    costStatus: string;
  };
  cost: {
    imageGenerationCredits: number | string;
    visionValidation: string;
    paidCallPerformed: boolean;
  };
}

type PreparationTab = 'overview' | 'characters' | 'first-frame' | 'settings' | 'review';
@Component({
  selector: 'app-render-preparation',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './render-preparation.page.html',
  styleUrl: './render-preparation.page.scss',
})
export class RenderPreparationPage implements OnInit, OnDestroy {
  queueContentId = signal('');
  queuePromptVersionId = signal('');
  queueValidationId = signal('');
  queueJobType = signal('VIDEO');
  renderTab = signal<'visual' | 'video'>('visual');
  workflowReview: any = null;
  workflowReviewId = '';
  promptVersionNumber = '';
  analysisId = '';
  workflowLoadSequence = 0;
  visualPreparation = signal<any | null>(null);
  firstFrameSpecification = signal('');
  firstFrameImagePrompt = signal('');
  visualPreparationSaving = signal(false);
  visualPreparationError = signal('');
  regenerationHandoffId = '';
  regenerationHandoff: any = null;
  queueModel = signal('byte-plus-seedance-2-mini');
  queueFirstFramePath = signal('');
  queueLoading = signal(false);
  queueError = signal('');
  queuedJobId = signal('');
  referenceAssets = signal<OpenArtReferenceAsset[]>([]);
  referenceCapabilities = signal<OpenArtCapabilities | null>(null);
  referenceSyncLoading = signal(false);
  referenceError = signal('');
  visualReferencePlan = signal<VisualReferencePlan | null>(null);
  visualReferenceLoading = signal<string | null>(null);
  visualReferenceError = signal('');
  visualReferenceProposal = signal<any | null>(null);
  visualReferenceValidation = signal<any | null>(null);

  // Start-frame generation state
  startFrameGenerating = signal(false);
  startFrameResult = signal<any | null>(null);
  startFrameBudget = signal(0.10);

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
    private router: Router,
  ) {}
  inspectPromptVisualReferences(): void {
    if (!this.workflowIdentityMatches(this.workflowReview)) {
      this.visualReferenceError.set(
        'Load the matching saved prompt review before preparing visual assets.',
      );
      return;
    }
    const sequence = this.workflowLoadSequence;
    const reviewId = this.workflowReviewId;
    this.visualReferenceLoading.set('prompt');
    this.visualReferenceError.set('');
    this.http
      .post<VisualReferencePlan>(
        `/api/v1/visual-reference-plans/prompts/${this.queueContentId()}/${this.queuePromptVersionId()}/inspect`,
        { model: this.queueModel() },
      )
      .subscribe({
        next: (plan) => {
          if (
            sequence !== this.workflowLoadSequence ||
            reviewId !== this.workflowReviewId ||
            !this.workflowReview ||
            Number(plan.contentId) !== Number(this.queueContentId()) ||
            Number(plan.promptVersionId) !== Number(this.queuePromptVersionId())
          )
            return;
          this.visualReferencePlan.set(plan);
          this.restoreAcceptedFirstFrame(plan);
          this.visualReferenceProposal.set(null);
          this.visualReferenceLoading.set(null);
        },
        error: (err) => {
          if (sequence !== this.workflowLoadSequence || reviewId !== this.workflowReviewId) return;
          this.visualReferenceLoading.set(null);
          this.visualReferenceError.set(
            err.error?.detail ||
              err.error?.message ||
              'Prompt-bound visual preparation could not be loaded.',
          );
        },
      });
  }

  private restoreAcceptedFirstFrame(plan: VisualReferencePlan): void {
    const binding = plan.referenceBindings?.find(
      (item) => item.role === 'FIRST_FRAME' && item.accepted,
    );
    if (!binding?.relativePath) return;
    const path = binding.relativePath;
    this.queueFirstFramePath.set(path.startsWith('/') ? path : `/data/${path}`);
  }

  async uploadPromptFirstFrame(event: Event): Promise<void> {
    const sequence = this.workflowLoadSequence;
    let plan = this.visualReferencePlan();
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (
      !this.workflowIdentityMatches(this.workflowReview) ||
      this.inputsChanged ||
      this.settingsDirty()
    ) {
      this.visualReferenceError.set(
        'Refresh the matching saved Production Review before uploading for this input contract.',
      );
      return;
    }
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      this.visualReferenceError.set('Choose a PNG, JPEG or WebP first-frame image.');
      return;
    }
    try {
      const dimensions = await this.decodeImage(file);
      if (sequence !== this.workflowLoadSequence) return;
      const parts = this.ratio.split(':').map(Number);
      if (
        dimensions.width < 16 ||
        dimensions.height < 16 ||
        !parts[0] ||
        !parts[1] ||
        Math.abs(dimensions.width / dimensions.height - parts[0] / parts[1]) /
          (parts[0] / parts[1]) >
          0.01
      ) {
        this.visualReferenceError.set(
          `The image is ${dimensions.width} × ${dimensions.height}; choose an image matching the saved ${this.ratio} aspect ratio. No acceptance was recorded.`,
        );
        return;
      }
    } catch {
      this.visualReferenceError.set(
        'The image could not be decoded. Choose a valid PNG, JPEG or WebP image.',
      );
      return;
    }
    if (!plan?.planId) {
      this.visualReferenceLoading.set('prompt');
      try {
        plan = await firstValueFrom(
          this.http
            .post<VisualReferencePlan>(
              `/api/v1/visual-reference-plans/prompts/${this.queueContentId()}/${this.queuePromptVersionId()}/inspect`,
              { model: this.queueModel() },
            )
            .pipe(takeUntil(this.destroyed)),
        );
        if (sequence !== this.workflowLoadSequence) return;
        if (
          !plan.planId ||
          Number(plan.contentId) !== Number(this.queueContentId()) ||
          Number(plan.promptVersionId) !== Number(this.queuePromptVersionId())
        )
          throw new Error('The image workspace did not match this saved source.');
        this.visualReferencePlan.set(plan);
      } catch (err: any) {
        if (sequence === this.workflowLoadSequence) {
          this.visualReferenceLoading.set(null);
          this.visualReferenceError.set(
            err.error?.detail ||
              err.message ||
              'The image workspace could not be prepared. Retry upload.',
          );
        }
        return;
      }
      this.visualReferenceLoading.set(null);
    }
    const uploadPlan = plan;
    const form = new FormData();
    form.append('file', file);
    this.visualReferenceError.set('');
    this.http
      .post(`/api/v1/visual-reference-plans/${uploadPlan.planId}/first-frame/upload`, form)
      .subscribe({
        next: () => {
          if (
            sequence === this.workflowLoadSequence &&
            this.visualReferencePlan()?.planId === uploadPlan.planId
          )
            this.loadPlan();
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.visualReferenceError.set(
              err.error?.detail ||
                err.error?.message ||
                'The first-frame image could not be uploaded.',
            );
        },
      });
  }

  acceptPromptFirstFrame(assetId: string): void {
    const sequence = this.workflowLoadSequence;
    const plan = this.visualReferencePlan();
    if (!plan?.planId) return;
    this.http
      .post(`/api/v1/visual-reference-plans/${plan.planId}/first-frame/accept`, {
        renderAssetId: assetId,
        ...this.acceptanceContext(),
      })
      .subscribe({
        next: () => {
          if (
            sequence === this.workflowLoadSequence &&
            this.visualReferencePlan()?.planId === plan.planId
          )
            this.persistAcceptedFrame(assetId);
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.visualReferenceError.set(
              err.error?.detail ||
                err.error?.message ||
                'The saved first frame could not be accepted.',
            );
        },
      });
  }

  acceptPromptImportedFirstFrame(assetId: string): void {
    const sequence = this.workflowLoadSequence;
    const plan = this.visualReferencePlan();
    if (!plan?.planId) return;
    this.http
      .post(
        `/api/v1/visual-reference-plans/${plan.planId}/first-frame/imported/${assetId}/accept`,
        this.acceptanceContext(),
      )
      .subscribe({
        next: () => {
          if (
            sequence === this.workflowLoadSequence &&
            this.visualReferencePlan()?.planId === plan.planId
          )
            this.persistAcceptedFrame(assetId);
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.visualReferenceError.set(
              err.error?.detail ||
                err.error?.message ||
                'The uploaded first frame could not be accepted.',
            );
        },
      });
  }

  qualityLink(stage = 5): string {
    return `/quality/detail?contentId=${encodeURIComponent(this.queueContentId())}&promptVersionId=${encodeURIComponent(this.queuePromptVersionId())}&studio=1&stage=${stage}${stage === 5 ? '&analysisTab=summary#findings-resolution' : ''}`;
  }

  revalidateRenderReadiness(): void {
    if (!this.workflowReviewId || !this.workflowIdentityMatches(this.workflowReview)) {
      this.queueError.set('The matching saved analysis is required to revalidate readiness.');
      return;
    }
    const sequence = this.workflowLoadSequence;
    this.queueLoading.set(true);
    this.queueError.set('');
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/records/${this.workflowReviewId}/canonical-validation`,
        {},
      )
      .subscribe({
        next: (result) => {
          if (
            sequence !== this.workflowLoadSequence ||
            !this.workflowIdentityMatches(this.workflowReview)
          )
            return;
          this.queueLoading.set(false);
          this.queueValidationId.set(String(result.validationRecordId || ''));
          if (this.workflowReview?.family8?.renderAuthorization?.status !== 'AUTHORIZED')
            this.queueError.set(
              'Validation was saved. Render authorization is still blocked or stale; reopen Production Review and refresh the exact review before queueing.',
            );
        },
        error: (err) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.queueLoading.set(false);
          this.queueError.set(
            err.error?.detail || err.error?.message || 'Canonical readiness validation failed.',
          );
        },
      });
  }

  queueRender(): void {
    if (this.queueLoading()) return;
    if (!this.workflowReviewId || !this.workflowReview) {
      this.queueError.set(
        'Open Render Preparation from the matching saved Quality Analysis record.',
      );
      return;
    }
    if (this.queueJobType() === 'FIRST_FRAME') {
      this.queueError.set(
        'First-frame generation requires separate explicit paid-call authorization and a positive cost ceiling. Use an existing image or upload one in Visual Preparation.',
      );
      return;
    }
    if (!this.canQueue()) {
      this.queueError.set(
        'Render is blocked: canonical authorization for this exact saved review is not AUTHORIZED.',
      );
      return;
    }
    if (!this.renderFrameIsCanonicallyVerified()) {
      this.queueError.set(
        'The selected first frame does not match the saved paired FIRST_FRAME and SILHOUETTE verification evidence. Revalidate this exact image before rendering.',
      );
      return;
    }
    const contentId = Number(this.queueContentId());
    const promptVersionId = Number(this.queuePromptVersionId());
    const validationRecordId = Number(this.queueValidationId());
    if (
      ![contentId, promptVersionId, validationRecordId].every(Number.isInteger) ||
      [contentId, promptVersionId, validationRecordId].some((value) => value <= 0)
    ) {
      this.queueError.set('Content, prompt version, and validation record IDs are required.');
      return;
    }
    if (this.regenerationHandoffId && !this.regenerationHandoff) {
      this.queueError.set('Regeneration handoff has not been loaded; queue admission is closed.');
      return;
    }
    this.queueLoading.set(true);
    this.queueError.set('');
    this.queuedJobId.set('');
    const firstFramePath = this.queueFirstFramePath().trim();
    const requestSequence = this.workflowLoadSequence;
    this.http
      .post<{ renderJobId: string }>(
        '/api/v1/render-jobs',
        {
          contentId,
          promptVersionId,
          validationRecordId,
          jobType: this.queueJobType(),
          openartModel: this.queueModel().trim() || 'byte-plus-seedance-2-mini',
          openartParams: this.workflowReview
            ? {
                workflowProfile: 'post-family-v1',
                workflowReviewId: this.workflowReviewId,
                workflowBindingHash: this.workflowReview.bindingHash,
                durationSeconds: this.workflowReview.generation.supportedRenderDuration,
                aspectRatio: this.workflowReview.generation.settings.aspectRatio,
                firstFrameImageId: firstFramePath,
                characterReferenceAssetId: this.characterBinding?.referenceId || null,
                mode: this.acceptanceContext().mode,
                ...(this.visualReferencePlan()?.planId
                  ? { visualReferencePlanId: this.visualReferencePlan()?.planId }
                  : {}),
                ...(this.regenerationHandoff
                  ? {
                      regenerationHandoffId: this.regenerationHandoffId,
                      parentVideoId: this.regenerationHandoff.parentVideoId,
                      parentVariantId: this.regenerationHandoff.parentVariantId,
                      parentAssetHash: this.regenerationHandoff.parentAssetHash,
                    }
                  : {}),
              }
            : firstFramePath
              ? {
                  firstFrameImageId: firstFramePath,
                  ...(this.visualReferencePlan()?.planId
                    ? { visualReferencePlanId: this.visualReferencePlan()?.planId }
                    : {}),
                }
              : {},
          requestPromptSha256: null,
        },
        {
          headers: {
            'Idempotency-Key':
              this.regenerationHandoffId && this.queueJobType() === 'VIDEO'
                ? this.regenerationHandoffId
                : crypto.randomUUID(),
          },
        },
      )
      .subscribe({
        next: (response) => {
          if (requestSequence !== this.workflowLoadSequence) return;
          this.queueLoading.set(false);
          this.queuedJobId.set(response.renderJobId);
        },
        error: (err) => {
          if (requestSequence !== this.workflowLoadSequence) return;
          this.queueLoading.set(false);
          this.queueError.set(
            err.error?.detail || err.error?.message || 'Render could not be queued.',
          );
        },
      });
  }

  workflowIdentityMatches(record: any): boolean {
    return (
      Number(record?.contentId) === Number(this.queueContentId()) &&
      Number(record?.promptVersionId) === Number(this.queuePromptVersionId()) &&
      (!this.analysisId || String(record?.recordId) === this.analysisId)
    );
  }

  renderFrameIsCanonicallyVerified(): boolean {
    const auth = this.workflowReview?.boundRequest?.authorizationEvidence?.visualEvidence || {};
    const first = auth.firstFrame || {};
    const silhouette = auth.silhouette || {};
    if (
      first.status !== 'PASS' ||
      silhouette.status !== 'PASS' ||
      !first.assetSha256 ||
      first.assetSha256 !== silhouette.assetSha256 ||
      !first.evidenceSetId ||
      first.evidenceSetId !== silhouette.evidenceSetId
    )
      return false;
    const accepted = this.visualReferencePlan()?.referenceBindings?.find(
      (item) => item.role === 'FIRST_FRAME' && item.accepted,
    );
    if (accepted)
      return (
        this.frameContextMatches(accepted) &&
        accepted.sha256 === first.assetSha256 &&
        Boolean(accepted.relativePath) &&
        (accepted.relativePath.startsWith('/')
          ? accepted.relativePath
          : `/data/${accepted.relativePath}`) === this.queueFirstFramePath()
      );
    const reference = (this.workflowReview?.boundRequest?.references || []).find(
      (item: any) => item.kind === 'FIRST_FRAME' && item.status === 'VERIFIED',
    );
    return Boolean(
      reference &&
      reference.sha256 === first.assetSha256 &&
      reference.relativePath === this.queueFirstFramePath(),
    );
  }

  draftFirstFramePrompt(): void {
    const review = this.workflowReview;
    const source = String(review?.boundRequest?.prompt || review?.originalPrompt || '').trim();
    const settings = review?.generation?.settings || review?.boundRequest?.settings || {};
    const character =
      review?.boundRequest?.mainCharacter ||
      review?.boundRequest?.mainCharacterName ||
      'the approved main character';
    const ratio = settings.aspectRatio || 'the saved aspect ratio';
    const opening = source
      .split(/\n\s*(?:3|[1-9]\d*)\s*[-–—]/, 1)[0]
      .replace(/^.*?(?:TIMED SHOT PLAN|OPENING)\s*/is, '')
      .trim();
    this.firstFrameSpecification.set(
      `Character: ${character}.\nScene and opening state: ${opening || 'Use the exact opening state from the approved production prompt.'}\nObject relationship: preserve every object and contact relationship stated in the opening.\nCamera and framing: clear readable composition at ${ratio}; keep the character and central object visible.\nContinuity: the composition must transition into the next saved production beat.\nRestrictions: use only approved character identity and source-supported details; no extra characters or invented mechanisms.`,
    );
    this.firstFrameImagePrompt.set(
      `Create the first frame of the approved video prompt. Show ${character} in the exact saved opening situation: ${opening || 'the source-approved opening state'}. Preserve the authoritative character design, clothing, object relationship and environment. Compose a readable ${ratio} image with the character and central object clearly visible, ready to continue into the next planned beat. Do not add characters, props, mechanisms or story events that are not in the approved source.`,
    );
  }

  saveVisualPreparation(): void {
    if (
      !this.workflowIdentityMatches(this.workflowReview) ||
      !this.firstFrameSpecification().trim() ||
      !this.firstFrameImagePrompt().trim()
    )
      return;
    const saveSequence = this.workflowLoadSequence;
    const contentId = Number(this.queueContentId());
    const promptVersionId = Number(this.queuePromptVersionId());
    const reviewId = this.workflowReviewId;
    this.visualPreparationSaving.set(true);
    this.visualPreparationError.set('');
    this.http
      .post<any>('/api/v1/intelligence/workflow/visual-preparation', {
        contentId,
        promptVersionId,
        reviewId,
        firstFrameSpecification: this.firstFrameSpecification(),
        firstFrameImagePrompt: this.firstFrameImagePrompt(),
        status: 'READY_FOR_REVIEW',
        providerCallPerformed: false,
        aspectRatio:
          this.workflowReview?.generation?.settings?.aspectRatio ||
          this.workflowReview?.boundRequest?.settings?.aspectRatio ||
          null,
        generator: this.queueModel(),
      })
      .subscribe({
        next: (value) => {
          if (saveSequence !== this.workflowLoadSequence) return;
          this.visualPreparation.set(value);
          this.visualPreparationSaving.set(false);
        },
        error: (err) => {
          if (saveSequence !== this.workflowLoadSequence) return;
          this.visualPreparationSaving.set(false);
          this.visualPreparationError.set(
            err.error?.detail || err.error?.message || 'Visual preparation could not be saved.',
          );
        },
      });
  }

  private loadVisualPreparation(
    loadSequence = this.workflowLoadSequence,
    contentId = Number(this.queueContentId()),
    promptVersionId = Number(this.queuePromptVersionId()),
  ): void {
    if (!contentId || !promptVersionId) return;
    this.http
      .get<any>('/api/v1/intelligence/workflow/visual-preparation', {
        params: { contentId, promptVersionId },
      })
      .subscribe({
        next: (value) => {
          if (
            loadSequence !== this.workflowLoadSequence ||
            contentId !== Number(this.queueContentId()) ||
            promptVersionId !== Number(this.queuePromptVersionId())
          )
            return;
          if (
            Number(value?.contentId) !== contentId ||
            Number(value?.promptVersionId) !== promptVersionId
          )
            return;
          this.visualPreparation.set(value);
          this.firstFrameSpecification.set(String(value.firstFrameSpecification || ''));
          this.firstFrameImagePrompt.set(String(value.firstFrameImagePrompt || ''));
        },
        error: () => {},
      });
  }

  tab = signal<PreparationTab>('overview');
  readonly tabs: Array<{ id: PreparationTab; label: string }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'characters', label: 'Character References' },
    { id: 'first-frame', label: 'First Frame' },
    { id: 'settings', label: 'Generator Settings' },
    { id: 'review', label: 'Final Review' },
  ];
  readonly steps = [
    'Idea',
    'Story',
    'Prompt',
    'Production Review',
    'Quality Analysis',
    'Repair',
    'Render Preparation',
    'Video QA',
  ];
  contextLoading = signal(true);
  characterId = '';
  characterName = '';
  characterReferences: any[] = [];
  characterBinding: any = null;
  characterLoading = false;
  selectedCharacterReference: any = null;
  selectedImage: any = null;
  selectedImageImported = false;
  previewError = false;
  previewDimensions = '';
  providerConfiguration: any = null;
  projectTitle = '';
  settings: any = {};
  savedSettings: any = null;
  inputsChanged = false;
  acceptedSinceValidation = false;
  settingsSaving = false;
  settingsError = '';
  private destroyed = new Subject<void>();
  private tabKey() {
    return `pompom-preparation-tab:${this.queueContentId()}:${this.queuePromptVersionId()}:${this.workflowReviewId}`;
  }
  selectTab(tab: PreparationTab, focusControl?: string) {
    this.tab.set(tab);
    if (this.workflowReviewId) {
      localStorage.setItem(this.tabKey(), tab);
      const currentUrl = new URL(window.location.href);
      if (
        currentUrl.searchParams.get('contentId') === this.queueContentId() &&
        currentUrl.searchParams.get('promptVersionId') === this.queuePromptVersionId() &&
        currentUrl.searchParams.get('workflowReviewId') === this.workflowReviewId
      ) {
        currentUrl.searchParams.set('tab', tab);
        window.history.replaceState(window.history.state, '', currentUrl.toString());
      }
    }
    if (focusControl) setTimeout(() => document.getElementById(focusControl)?.focus());
  }
  get ratio(): string {
    return (
      this.savedSettings?.aspectRatio ||
      this.workflowReview?.generation?.settings?.aspectRatio ||
      ''
    );
  }
  get title(): string {
    return (
      this.projectTitle ||
      this.workflowReview?.contentTitle ||
      this.workflowReview?.boundRequest?.contentTitle ||
      this.workflowReview?.boundRequest?.title ||
      `Project ${this.queueContentId()}`
    );
  }
  get generatorLabel(): string {
    return (
      (
        {
          SEEDANCE_2_0_MINI: 'Seedance 2.0 Mini',
          SEEDANCE_2_0: 'Seedance 2.0',
          SEEDANCE_2_5: 'Seedance 2.5',
        } as any
      )[this.settings.generator] ||
      this.queueModel() ||
      'Unresolved generator'
    );
  }
  acceptanceContext() {
    return {
      aspectRatio: this.ratio,
      model: this.queueModel(),
      characterReferenceAssetId: this.characterBinding?.referenceId || '',
      mode:
        this.workflowReview?.generation?.mode ||
        this.workflowReview?.generation?.settings?.generationMode ||
        'image2video',
    };
  }
  canQueue(): boolean {
    return (
      (!this.regenerationHandoffId || !!this.regenerationHandoff) &&
      !!this.workflowReviewId &&
      this.workflowIdentityMatches(this.workflowReview) &&
      this.characterReady &&
      this.frameReady &&
      !!this.visualReferencePlan()?.planId &&
      !this.inputsChanged &&
      !this.acceptedSinceValidation &&
      !this.settingsDirty() &&
      this.workflowReview?.family8?.renderAuthorization?.status === 'AUTHORIZED' &&
      !!this.queueValidationId() &&
      this.renderFrameIsCanonicallyVerified()
    );
  }
  settingsDirty(): boolean {
    return (
      !!this.savedSettings &&
      ['generator', 'desiredDuration', 'aspectRatio'].some(
        (key) => String(this.settings[key] || '') !== String(this.savedSettings[key] || ''),
      )
    );
  }
  get characterReady(): boolean {
    return (
      !!this.characterBinding?.referenceId &&
      this.characterBinding?.approvalStatus === 'APPROVED' &&
      !!this.characterBinding?.sha256
    );
  }
  get frameReady(): boolean {
    return !!this.visualReferencePlan()?.referenceBindings?.some(
      (ref) => ref.role === 'FIRST_FRAME' && ref.accepted && this.frameContextMatches(ref),
    );
  }

  /** Check if start-frame generation is available. */
  canGenerateStartFrame(): boolean {
    return (
      !!this.workflowReview &&
      !!this.workflowReviewId &&
      this.workflowIdentityMatches(this.workflowReview) &&
      this.characterReady &&
      !!this.ratio &&
      !this.inputsChanged &&
      !this.settingsDirty() &&
      this.startFrameBudget() > 0
    );
  }

  /** Generate a start-frame candidate image. */
  generateStartFrame(): void {
    if (!this.canGenerateStartFrame() || this.startFrameGenerating()) return;
    const sequence = this.workflowLoadSequence;
    this.startFrameGenerating.set(true);
    this.startFrameResult.set(null);
    this.visualReferenceError.set('');

    const prompt = String(
      this.workflowReview?.boundRequest?.prompt ||
      this.workflowReview?.originalPrompt ||
      '',
    ).trim();
    const character =
      this.workflowReview?.boundRequest?.mainCharacter ||
      this.workflowReview?.boundRequest?.mainCharacterName ||
      this.characterName ||
      '';

    this.http
      .post<any>('/api/v1/intelligence/workflow/start-frame/generate', {
        prompt,
        contentId: Number(this.queueContentId()),
        promptVersionId: Number(this.queuePromptVersionId()),
        characterName: character,
        characterDescription: this.characterBinding?.description || '',
        characterId: this.characterBinding?.characterId || '',
        referenceId: this.characterBinding?.referenceId || '',
        referenceSha256: this.characterBinding?.sha256 || '',
        aspectRatio: this.ratio,
        contentProfile: this.workflowReview?.boundRequest?.contentProfile || 'AUTO',
        generator: this.queueModel(),
        maxCostUsd: this.startFrameBudget(),
        promptFingerprint: this.workflowReview?.boundRequest?.promptSha256 || '',
        sourceRevisionId: this.workflowReview?.boundRequest?.sourceRevisionId || '',
      })
      .subscribe({
        next: (result) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.startFrameGenerating.set(false);
          this.startFrameResult.set(result);
          if (result.status !== 'GENERATED') {
            this.visualReferenceError.set(
              result.reason || 'Start-frame generation failed.',
            );
          }
        },
        error: (err) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.startFrameGenerating.set(false);
          this.visualReferenceError.set(
            err.error?.detail ||
              err.error?.message ||
              'Start-frame generation request failed.',
          );
        },
      });
  }

  /** Regenerate start frame (clears previous result). */
  regenerateStartFrame(): void {
    this.startFrameResult.set(null);
    this.generateStartFrame();
  }

  /** Reject the current start-frame candidate. */
  rejectStartFrameCandidate(): void {
    const result = this.startFrameResult();
    if (!result || !result.databaseId) {
      this.startFrameResult.set(null);
      return;
    }
    this.http.post<any>('/api/v1/intelligence/workflow/start-frame/reject', {
      candidateId: result.databaseId,
      contentId: Number(this.queueContentId()),
      promptVersionId: Number(this.queuePromptVersionId()),
      reason: 'User rejected candidate',
    }).subscribe({
      next: () => this.startFrameResult.set(null),
      error: () => this.startFrameResult.set(null),
    });
  }

  /** Accept the generated start-frame candidate. */
  acceptStartFrameCandidate(): void {
    const result = this.startFrameResult();
    if (!result || result.status !== 'GENERATED') return;
    if (!result.databaseId) {
      this.visualReferenceError.set('Candidate not persisted. Please regenerate.');
      return;
    }
    this.visualReferenceError.set('');
    this.http.post<any>('/api/v1/intelligence/workflow/start-frame/accept', {
      candidateId: result.databaseId,
      contentId: Number(this.queueContentId()),
      promptVersionId: Number(this.queuePromptVersionId()),
    }).subscribe({
      next: () => {
        this.startFrameResult.set({ ...result, status: 'ACCEPTED' });
        this.loadPlan();
      },
      error: (err) => {
        this.visualReferenceError.set(
          err.error?.detail ||
          err.error?.message ||
          'The generated start frame could not be accepted.',
          );
        },
      });
  }
  frameContextMatches(ref: any): boolean {
    const evidence = ref.evidence || {};
    const context = this.acceptanceContext();
    return (
      !!evidence.promptHash &&
      evidence.promptHash === this.visualReferencePlan()?.promptSha256 &&
      evidence.aspectRatio === context.aspectRatio &&
      evidence.model === context.model &&
      String(evidence.characterReferenceAssetId || '') ===
        String(context.characterReferenceAssetId || '') &&
      evidence.mode === context.mode &&
      evidence.checksum === ref.sha256
    );
  }
  get nextTab(): PreparationTab {
    return !this.characterReady
      ? 'characters'
      : !this.frameReady
        ? 'first-frame'
        : this.settingsDirty() || this.inputsChanged
          ? 'settings'
          : 'review';
  }
  get nextLabel(): string {
    return this.nextTab === 'characters'
      ? 'Select an approved character reference'
      : this.nextTab === 'first-frame'
        ? 'Prepare and accept the opening image'
        : this.nextTab === 'settings'
          ? 'Review changed generator settings'
          : 'Review canonical rendering requirements';
  }
  imageUrl(image: any, imported: boolean): string {
    return imported
      ? `/api/v1/visual-reference-plans/${this.visualReferencePlan()?.planId}/assets/${image.assetId}/media`
      : `/api/v1/render-assets/${image.assetId}/media`;
  }
  selectImage(image: any, imported: boolean) {
    this.selectedImage = image;
    this.selectedImageImported = imported;
    this.previewError = false;
    this.previewDimensions = '';
  }
  onPreviewLoad(event: Event) {
    const image = event.target as HTMLImageElement;
    this.previewDimensions = `${image.naturalWidth} × ${image.naturalHeight}`;
  }
  acceptSelectedFrame() {
    if (!this.selectedImage || this.inputsChanged || this.settingsDirty()) return;
    this.acceptedSinceValidation = true;
    if (this.selectedImageImported) this.acceptPromptImportedFirstFrame(this.selectedImage.assetId);
    else this.acceptPromptFirstFrame(this.selectedImage.assetId);
  }
  loadPlan(): void {
    if (!this.workflowIdentityMatches(this.workflowReview)) return;
    const sequence = this.workflowLoadSequence;
    this.http
      .get<VisualReferencePlan>(
        `/api/v1/visual-reference-plans/prompts/${this.queueContentId()}/${this.queuePromptVersionId()}`,
        { params: { model: this.queueModel() } },
      )
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: (plan) => {
          if (sequence !== this.workflowLoadSequence) return;
          if (
            Number(plan.contentId) !== Number(this.queueContentId()) ||
            Number(plan.promptVersionId) !== Number(this.queuePromptVersionId())
          ) {
            this.visualReferenceError.set('The image plan belongs to another immutable source.');
            return;
          }
          this.visualReferencePlan.set(plan);
          this.restoreAcceptedFirstFrame(plan);
          const accepted = plan.referenceBindings?.find(
            (ref) => ref.role === 'FIRST_FRAME' && ref.accepted,
          );
          if (accepted) this.selectImage(accepted, true);
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.visualReferenceError.set(
              err.error?.detail ||
                'Existing first-frame images could not be loaded. Use Load existing images to retry.',
            );
        },
      });
  }
  loadCharacters(): void {
    const sequence = this.workflowLoadSequence;
    this.characterLoading = true;
    this.http
      .get<any[]>('/api/v1/characters')
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: (rows) => {
          if (sequence !== this.workflowLoadSequence) return;
          const bound = this.workflowReview?.boundRequest || {};
          const named = String(bound.mainCharacter || bound.mainCharacterName || '');
          const prompt = String(bound.prompt || this.workflowReview?.originalPrompt || '');
          const character =
            rows.find((row) => row.id === bound.characterId) ||
            rows.find((row) =>
              [row.name, row.displayName, row.characterName, ...(row.aliases || [])]
                .filter(Boolean)
                .some((name) =>
                  named
                    ? String(name).toLowerCase() === named.toLowerCase()
                    : new RegExp(
                        `\\b${String(name).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`,
                        'i',
                      ).test(prompt),
                ),
            );
          this.characterLoading = false;
          if (!character) {
            this.referenceError.set(
              'Character identity could not be resolved from this saved prompt. Review the source in Production Review.',
            );
            return;
          }
          this.characterId = character.id;
          this.characterName = character.name || character.displayName;
          this.loadCharacterAssets(sequence);
          this.loadWorkspaceReferences();
        },
        error: () => {
          this.characterLoading = false;
          this.referenceError.set(
            'Character catalog could not be loaded. Retry to restore references.',
          );
        },
      });
  }
  loadCharacterAssets(sequence = this.workflowLoadSequence): void {
    this.http
      .get<any[]>(`/api/v1/characters/${this.characterId}/references`)
      .pipe(takeUntil(this.destroyed))
      .subscribe({
        next: (rows) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.characterReferences = rows;
          this.http
            .get<any>('/api/v1/intelligence/workflow/production-review/reference-binding', {
              params: {
                contentId: this.queueContentId(),
                promptVersionId: this.queuePromptVersionId(),
              },
            })
            .pipe(takeUntil(this.destroyed))
            .subscribe({
              next: (binding) => {
                if (sequence !== this.workflowLoadSequence) return;
                const ref = rows.find(
                  (row) =>
                    row.id === binding.referenceId &&
                    row.sha256 === binding.sha256 &&
                    row.status === 'APPROVED',
                );
                this.characterBinding = ref ? binding : null;
                if (ref) {
                  this.selectedCharacterReference = ref;
                  const reviewed = (this.workflowReview?.boundRequest?.references || []).find(
                    (item: any) => item.kind === 'CHARACTER_REFERENCE',
                  );
                  if (
                    !reviewed ||
                    (reviewed.assetId || reviewed.id) !== binding.referenceId ||
                    reviewed.sha256 !== binding.sha256
                  ) {
                    this.inputsChanged = true;
                    this.queueValidationId.set('');
                  }
                }
              },
              error: (err) => {
                if (sequence === this.workflowLoadSequence)
                  this.referenceError.set(
                    err.error?.detail ||
                      'Saved character binding could not be restored. Retry to verify the exact reference.',
                  );
              },
            });
        },
        error: () => {
          if (sequence === this.workflowLoadSequence)
            this.referenceError.set(
              'Character images could not be loaded. Retry the asset catalog.',
            );
        },
      });
  }
  bindCharacterReference(ref: any): void {
    if (ref.status !== 'APPROVED' || !this.characterId) return;
    const sequence = this.workflowLoadSequence;
    this.http
      .post<any>('/api/v1/intelligence/workflow/production-review/reference-binding', {
        contentId: Number(this.queueContentId()),
        promptVersionId: Number(this.queuePromptVersionId()),
        characterId: this.characterId,
        referenceId: ref.id,
      })
      .subscribe({
        next: (binding) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.characterBinding = binding;
          this.selectedCharacterReference = ref;
          this.inputsChanged = true;
          this.queueValidationId.set('');
          this.queueError.set(
            'Character binding changed. Refresh the saved Production Review and canonical analysis before queueing.',
          );
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.referenceError.set(err.error?.detail || 'Reference binding could not be saved.');
        },
      });
  }
  uploadCharacter(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file || !this.characterId) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      this.referenceError.set('Choose a PNG, JPEG or WebP reference image.');
      return;
    }
    const sequence = this.workflowLoadSequence;
    const form = new FormData();
    form.append('file', file);
    form.append('description', `Operator upload for ${this.characterName}`);
    this.http.post(`/api/v1/characters/${this.characterId}/references`, form).subscribe({
      next: () => {
        if (sequence === this.workflowLoadSequence) this.loadCharacterAssets();
      },
      error: (err) => {
        if (sequence === this.workflowLoadSequence)
          this.referenceError.set(err.error?.detail || 'Character image upload failed.');
      },
    });
  }
  approveCharacter(ref: any): void {
    const sequence = this.workflowLoadSequence;
    this.http
      .post(`/api/v1/characters/${this.characterId}/references/${ref.id}/approve`, {
        reviewer: 'local-user',
      })
      .subscribe({
        next: () => {
          if (sequence === this.workflowLoadSequence) this.loadCharacterAssets();
        },
        error: (err) => {
          if (sequence === this.workflowLoadSequence)
            this.referenceError.set(err.error?.detail || 'Reference approval failed.');
        },
      });
  }
  saveSettings(): void {
    if (!this.workflowIdentityMatches(this.workflowReview)) return;
    const sequence = this.workflowLoadSequence;
    this.settingsSaving = true;
    this.settingsError = '';
    this.http
      .post<any>('/api/v1/intelligence/workflow/production-settings', {
        ...this.settings,
        contentId: Number(this.queueContentId()),
        promptVersionId: Number(this.queuePromptVersionId()),
      })
      .subscribe({
        next: (value) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.savedSettings = { ...value };
          this.settings = { ...value };
          this.settingsSaving = false;
          this.inputsChanged = true;
          this.queueValidationId.set('');
          this.queueError.set(
            'Settings saved. Refresh Production Review and analyze this exact contract before accepting or queueing.',
          );
        },
        error: (err) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.settingsSaving = false;
          this.settingsError = err.error?.detail || 'Generator settings could not be saved.';
        },
      });
  }
  ngOnInit(): void {
    this.route.queryParamMap.pipe(takeUntil(this.destroyed)).subscribe((params) => {
      const sequence = ++this.workflowLoadSequence;
      this.contextLoading.set(true);
      this.providerConfiguration = null;
      this.projectTitle = '';
      this.characterId = '';
      this.characterName = '';
      this.characterLoading = false;
      this.workspaceReferences = [];
      this.workspaceSearched = false;
      this.referenceImporting = false;
      this.previewError = false;
      this.previewDimensions = '';
      this.settingsError = '';
      this.settingsSaving = false;
      this.visualReferenceLoading.set(null);
      this.visualPreparationSaving.set(false);
      this.queueLoading.set(false);
      this.queuedJobId.set('');
      this.workflowReview = null;
      this.characterBinding = null;
      this.characterReferences = [];
      this.selectedCharacterReference = null;
      this.selectedImage = null;
      this.visualReferencePlan.set(null);
      this.visualPreparation.set(null);
      this.firstFrameSpecification.set('');
      this.firstFrameImagePrompt.set('');
      this.inputsChanged = false;
      this.acceptedSinceValidation = false;
      this.savedSettings = null;
      this.settings = {};
      this.queueError.set('');
      this.queueFirstFramePath.set('');
      this.visualReferenceError.set('');
      this.referenceError.set('');
      this.queueContentId.set(params.get('contentId') || '');
      this.queuePromptVersionId.set(params.get('promptVersionId') || '');
      this.queueValidationId.set(params.get('validationRecordId') || '');
      this.workflowReviewId = params.get('workflowReviewId') || '';
      this.regenerationHandoffId = params.get('regenerationHandoffId') || '';
      this.regenerationHandoff = null;
      this.analysisId = params.get('analysisId') || '';
      this.promptVersionNumber = params.get('promptVersionNumber') || '';
      const requested = params.get('tab') || localStorage.getItem(this.tabKey());
      this.tab.set(
        this.tabs.some((tab) => tab.id === requested) ? (requested as PreparationTab) : 'overview',
      );
      if (
        !this.workflowReviewId ||
        ![this.queueContentId(), this.queuePromptVersionId()].every((id) => /^[1-9]\d*$/.test(id))
      ) {
        this.contextLoading.set(false);
        return;
      }
      if (this.regenerationHandoffId)
        this.http
          .get<any>(`/api/v1/intelligence/workflow/records/${this.regenerationHandoffId}`)
          .pipe(takeUntil(this.destroyed))
          .subscribe({
            next: (handoff) => {
              if (sequence !== this.workflowLoadSequence) return;
              if (
                Number(handoff.contentId) !== Number(this.queueContentId()) ||
                Number(handoff.promptVersionId) !== Number(this.queuePromptVersionId())
              ) {
                this.queueError.set('Regeneration handoff belongs to another saved source.');
                return;
              }
              this.regenerationHandoff = handoff;
            },
            error: () => {
              if (sequence === this.workflowLoadSequence)
                this.queueError.set(
                  'Regeneration handoff could not be loaded; queue admission is closed.',
                );
            },
          });
      this.http
        .get<any>(`/api/v1/intelligence/workflow/records/${this.workflowReviewId}`)
        .pipe(takeUntil(this.destroyed))
        .subscribe({
          next: (review) => {
            if (sequence !== this.workflowLoadSequence) return;
            this.contextLoading.set(false);
            if (!this.workflowIdentityMatches(review)) {
              this.queueError.set(
                'The saved review does not match this content, immutable prompt version, or analysis run.',
              );
              return;
            }
            this.workflowReview = review;
            this.queueModel.set(review.generation?.apiModelId || '');
            this.queueFirstFramePath.set(review.generation?.settings?.startFrame?.id || '');
            this.settings = {
              generator: review.boundRequest?.generator || 'SEEDANCE_2_0_MINI',
              desiredDuration: review.generation?.supportedRenderDuration,
              aspectRatio: review.generation?.settings?.aspectRatio,
              contentProfile: review.boundRequest?.contentProfile || 'AUTO',
              openingStrategy: review.boundRequest?.openingStrategy || 'AUTO',
              qualityJustification: review.boundRequest?.qualityJustification || '',
            };
            this.savedSettings = { ...this.settings };
            this.loadVisualPreparation(sequence);
            this.loadPlan();
            this.loadCharacters();
            this.http
              .get<any>(`/api/v1/intelligence/contents/${this.queueContentId()}`)
              .pipe(takeUntil(this.destroyed))
              .subscribe({
                next: (content) => {
                  if (
                    sequence === this.workflowLoadSequence &&
                    String(content.id) === this.queueContentId()
                  )
                    this.projectTitle = content.title || '';
                },
                error: () => {},
              });
            this.http
              .get<any>('/api/v1/intelligence/workflow/production-settings', {
                params: {
                  contentId: this.queueContentId(),
                  promptVersionId: this.queuePromptVersionId(),
                },
              })
              .pipe(takeUntil(this.destroyed))
              .subscribe({
                next: (value) => {
                  if (sequence !== this.workflowLoadSequence) return;
                  this.settings = { ...this.settings, ...value };
                  this.savedSettings = { ...this.settings };
                  const bound = review.generation?.settings || {};
                  if (
                    value.aspectRatio !== bound.aspectRatio ||
                    Number(value.desiredDuration) !==
                      Number(
                        review.boundRequest?.desiredDuration ||
                          review.generation?.supportedRenderDuration,
                      ) ||
                    value.generator !== review.boundRequest?.generator
                  ) {
                    this.inputsChanged = true;
                    this.queueValidationId.set('');
                  }
                },
                error: () => {},
              });
            this.http
              .get<any>('/api/v1/openart/references/configuration')
              .pipe(takeUntil(this.destroyed))
              .subscribe({
                next: (value) => {
                  if (sequence === this.workflowLoadSequence) this.providerConfiguration = value;
                },
                error: () => {},
              });
            this.http
              .get<OpenArtCapabilities>('/api/v1/openart/references/capabilities')
              .pipe(takeUntil(this.destroyed))
              .subscribe({
                next: (value) => this.referenceCapabilities.set(value),
                error: () => this.referenceCapabilities.set(null),
              });
          },
          error: () => {
            if (sequence === this.workflowLoadSequence) {
              this.contextLoading.set(false);
              this.queueError.set(
                'The saved review could not be loaded. Reopen this exact project from Quality Analysis.',
              );
            }
          },
        });
    });
  }
  ngOnDestroy(): void {
    this.destroyed.next();
    this.destroyed.complete();
    ++this.workflowLoadSequence;
  }

  workspaceReferences: any[] = [];
  workspaceSearched = false;
  referenceImporting = false;
  workspaceImageUrl(path: string): string {
    return `/api/v1/characters/${this.characterId}/workspace-references/image?relativePath=${encodeURIComponent(path)}`;
  }
  loadWorkspaceReferences(): void {
    if (!this.characterId) return;
    const sequence = this.workflowLoadSequence;
    this.http.get<any[]>(`/api/v1/characters/${this.characterId}/workspace-references`).subscribe({
      next: (rows) => {
        if (sequence !== this.workflowLoadSequence) return;
        this.workspaceReferences = rows.map((row) => ({ ...row, name: row.displayName }));
        this.workspaceSearched = true;
      },
      error: (err) => {
        if (sequence === this.workflowLoadSequence)
          this.referenceError.set(
            err.error?.detail ||
              'Local workspace images could not be discovered. Retry or upload a reference.',
          );
      },
    });
  }
  importWorkspaceReference(image: any): void {
    if (!this.characterId) return;
    const sequence = this.workflowLoadSequence;
    this.referenceImporting = true;
    this.http
      .post(`/api/v1/characters/${this.characterId}/workspace-references/import`, {
        relativePath: image.relativePath,
      })
      .subscribe({
        next: () => {
          if (sequence !== this.workflowLoadSequence) return;
          this.referenceImporting = false;
          this.loadCharacterAssets();
        },
        error: (err) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.referenceImporting = false;
          this.referenceError.set(err.error?.detail || 'Workspace import failed.');
        },
      });
  }

  private persistAcceptedFrame(assetId: string): void {
    const sequence = this.workflowLoadSequence;
    this.http
      .get<VisualReferencePlan>(
        `/api/v1/visual-reference-plans/prompts/${this.queueContentId()}/${this.queuePromptVersionId()}`,
        { params: { model: this.queueModel() } },
      )
      .subscribe({
        next: (plan) => {
          if (sequence !== this.workflowLoadSequence) return;
          this.visualReferencePlan.set(plan);
          this.restoreAcceptedFirstFrame(plan);
          const ref = plan.referenceBindings?.find(
            (row) => row.role === 'FIRST_FRAME' && row.accepted,
          );
          if (!ref) {
            this.visualReferenceError.set(
              'Acceptance did not produce a current exact-source binding. Refresh the image plan.',
            );
            return;
          }
          this.selectImage(ref, true);
          const startFrame = {
            id: this.queueFirstFramePath(),
            url: ref.mediaUrl || this.imageUrl(ref, true),
            assetId: ref.assetId,
            sha256: ref.sha256,
            acceptanceEvidence: ref.evidence,
          };
          this.http
            .post<any>('/api/v1/intelligence/workflow/production-settings', {
              ...this.savedSettings,
              contentId: Number(this.queueContentId()),
              promptVersionId: Number(this.queuePromptVersionId()),
              startFrame,
            })
            .subscribe({
              next: (value) => {
                if (sequence !== this.workflowLoadSequence) return;
                this.savedSettings = value;
                this.settings = { ...value };
                this.queueValidationId.set('');
                this.queueError.set(
                  'First-frame acceptance saved and bound to production settings. Return to Production Review to refresh canonical analysis for this exact image.',
                );
              },
              error: (err) =>
                this.visualReferenceError.set(
                  err.error?.detail ||
                    'Image was accepted, but production settings could not be updated. Retry acceptance binding before revalidation.',
                ),
            });
        },
        error: (err) =>
          this.visualReferenceError.set(
            err.error?.detail || 'Accepted image binding could not be restored.',
          ),
      });
  }

  private decodeImage(file: File): Promise<{ width: number; height: number }> {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        URL.revokeObjectURL(url);
        resolve({ width: image.naturalWidth, height: image.naturalHeight });
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Invalid image'));
      };
      image.src = url;
    });
  }
  onTabKeydown(event: KeyboardEvent, current: PreparationTab): void {
    const index = this.tabs.findIndex((item) => item.id === current);
    const next =
      event.key === 'ArrowRight'
        ? (index + 1) % this.tabs.length
        : event.key === 'ArrowLeft'
          ? (index + this.tabs.length - 1) % this.tabs.length
          : event.key === 'Home'
            ? 0
            : event.key === 'End'
              ? this.tabs.length - 1
              : -1;
    if (next < 0) return;
    event.preventDefault();
    this.selectTab(this.tabs[next].id);
    document.getElementById(`tab-${this.tabs[next].id}`)?.focus();
  }
  authorizationLabel(): string {
    const status = this.workflowReview?.family8?.renderAuthorization?.status;
    if (status === 'AUTHORIZED')
      return this.canQueue()
        ? 'Authorized for current inputs'
        : 'Saved authorization needs revalidation';
    if (status === 'BLOCKED_TECHNICAL_FAILURE') return 'Blocked: readiness validation failed';
    if (String(status || '').startsWith('BLOCKED')) return 'Blocked: outstanding requirements';
    return 'Unknown: revalidation required';
  }
  humanReason(reason: any): string {
    const text = String(
      reason?.message ||
        reason?.reason ||
        reason?.detail ||
        reason ||
        'Canonical evidence review is required.',
    );
    if (
      /(?:start.?frame|first.?frame)/i.test(text) &&
      /missing|unknown|absent|not provided/i.test(text)
    )
      return 'Opening image is missing or its evidence needs review.';
    return text
      .replace(/\bstartFrame\b/g, 'opening image')
      .replace(/\bFIRST_FRAME\b/g, 'opening image')
      .replace(/\bcharacterReference\b/g, 'character reference')
      .replace(/\bBLOCKED_TECHNICAL_FAILURE\b/g, 'Readiness validation failed');
  }
}
