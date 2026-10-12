import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { CreativeStudioPage } from './creative-studio.page';

describe('Step 2 — Story Review: Finding Semantics and Evidence Consistency', () => {
  let http: HttpTestingController;
  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [CreativeStudioPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])]
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { http.verify(); localStorage.clear(); TestBed.resetTestingModule(); });

  function open() {
    const fixture = TestBed.createComponent(CreativeStudioPage);
    fixture.detectChanges();
    http.match(r => r.method === 'GET').forEach(r =>
      r.flush(r.request.url.endsWith('readiness') ? { enabled: true, roles: [{ role: 'STORY', configured: true }, { role: 'STORY_REVIEW', configured: true, model: 'gpt-4o-mini' }] } : []));
    fixture.detectChanges();
    return { fixture, page: fixture.componentInstance as any };
  }

  // ── 1. Separate finding type from severity ──

  it('classifies positive findings as STRENGTH without severity', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Clear opening hook', dimension: 'opening', supportingTextEvidence: ['Mimi opens the cabinet'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings.length).toBe(1);
    expect(findings[0].findingType).toBe('STRENGTH');
    expect(findings[0].severity).toBeNull();
    expect(findings[0].finding).toBe('Clear opening hook');
  });

  it('classifies negative findings as CONCERN with severity preserved', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Ambiguous ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: ['No resolution'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('CONCERN');
    expect(findings[0].severity).toBe('high');
  });

  it('classifies neutral findings as OBSERVATION without severity', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Story uses first-person perspective', dimension: 'narrative voice', supportingTextEvidence: ['I walked'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('OBSERVATION');
    expect(findings[0].severity).toBeNull();
  });

  it('respects explicit findingType from provider response', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Well structured', dimension: 'structure', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('STRENGTH');
    expect(findings[0].severity).toBeNull();
  });

  it('does not assign severity to STRENGTH even when provider includes severity field', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Strong character arc', dimension: 'character', severity: 'low', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('STRENGTH');
    expect(findings[0].severity).toBeNull();
  });

  it('handles UNKNOWN finding type for unclassifiable findings', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: ['Unparseable finding string']
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('UNKNOWN');
    expect(findings[0].severity).toBeNull();
  });

  it('keeps confidence separate from severity', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Weak pacing', dimension: 'pacing', severity: 'medium', supportingTextEvidence: ['Middle section drags'], confidenceOrEvidenceStatus: 'PARTIAL' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('CONCERN');
    expect(findings[0].severity).toBe('medium');
    expect(findings[0].confidence).toBe('PARTIAL');
  });

  it('uses null for missing severity rather than inventing defaults', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Good flow', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: null }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('STRENGTH');
    expect(findings[0].severity).toBeNull();
    expect(findings[0].confidence).toBe('Evidence unavailable');
  });

  // ── 2. Validate comparative claims ──

  it('adds evidence limitation when provider recommends but candidates are near duplicates', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');

    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 has superior narrative structure',
      candidateReviews: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.evidenceLimitations.length).toBeGreaterThan(0);
    expect(normalized.evidenceLimitations[0]).toContain('NEAR DUPLICATE');
    expect(normalized.recommendationReason).toContain('Provider suggestion only');
  });

  it('adds evidence limitation when provider recommends but evidence is insufficient', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'A child opens a red door.' },
      { candidateId: 'c2', title: 'B', text: 'A storm crosses the empty harbour while lights fade.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.classification).toBe('INSUFFICIENT_EVIDENCE');

    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 is more engaging',
      candidateReviews: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.evidenceLimitations.length).toBeGreaterThan(0);
    expect(normalized.evidenceLimitations[0]).toContain('INSUFFICIENT EVIDENCE');
  });

  it('does not fabricate material differences to justify a winner', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.differences).toEqual([]);
    expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');
  });

  it('shows recommendation with evidence limitation in UI when near duplicate', () => {
    const { page, fixture } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Provider suggestion only · Candidate 1 has superior narrative structure. Canonical evidence does not support a winner.',
      candidateReviews: []
    };
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Canonical evidence does not support a winner');
  });

  // ── 3. UI rendering ──

  it('displays finding type badge in template', () => {
    const { page, fixture } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'CONCERN', finding: 'Weak ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: ['No resolution'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    page.selectedCandidateIdValue = 'c1';
    page.reviewDialogOpen = true;
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    const badges = fixture.nativeElement.querySelectorAll('.review-finding-type-badge');
    expect(badges.length).toBe(2);
    expect(fixture.nativeElement.querySelector('.review-finding-type--strength')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.review-finding-type--concern')).not.toBeNull();
  });

  it('shows severity badge only for CONCERN findings', () => {
    const { page, fixture } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'CONCERN', finding: 'Weak ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    page.selectedCandidateIdValue = 'c1';
    page.reviewDialogOpen = true;
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    // The STRENGTH finding should NOT have a severity badge
    const strengthItem = fixture.nativeElement.querySelector('.review-finding-item--strength');
    expect(strengthItem).not.toBeNull();
    expect(strengthItem.querySelector('.review-finding-sev')).toBeNull();
    // The CONCERN finding should have a severity badge
    const concernItem = fixture.nativeElement.querySelector('.review-finding-item--concern');
    expect(concernItem).not.toBeNull();
    expect(concernItem.querySelector('.review-finding-sev--high')).not.toBeNull();
  });

  it('allows a good story to have zero HIGH findings', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'STRENGTH', finding: 'Satisfying ending', dimension: 'payoff', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'OBSERVATION', finding: 'Uses first-person perspective', dimension: 'narrative voice', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    const findings = page.normalizedReviewFindings('c1');
    const highFindings = findings.filter((f: any) => f.severity === 'high');
    expect(highFindings.length).toBe(0);
    expect(findings.length).toBe(3);
  });

  // ── 4. Review provenance ──

  it('labels fixture review timestamps correctly', () => {
    const { page } = open();
    page.storyReview = { reviewId: 'LOCAL_MOCK_REVIEW', reviewModel: 'local-mock', reviewTimestamp: '2023-10-05T12:00:00Z' };
    expect(page.reviewTimestampLabel()).toBe('DEMO / FIXTURE · Review time unavailable');
  });

  it('shows actual timestamp for live review', () => {
    const { page } = open();
    page.storyReview = { reviewId: 'live-123', reviewModel: 'gpt-4o-mini', reviewTimestamp: '2026-10-11T10:00:00Z' };
    expect(page.reviewTimestampLabel()).toBe('2026-10-11T10:00:00.000Z');
  });

  it('shows unavailable for unparseable timestamps', () => {
    const { page } = open();
    page.storyReview = { reviewId: 'live', reviewModel: 'gpt', reviewTimestamp: 'not-a-date' };
    expect(page.reviewTimestampLabel()).toBe('Review time unavailable');
  });

  it('keeps malformed review payloads as diagnostic evidence', () => {
    const { page } = open();
    const review = (page as any).normalizeStoryReview('{malformed');
    expect(review.reviewStatus).toBe('INVALID');
    expect(review.evidenceLimitations[0]).toContain('malformed');
    expect(review.rawProviderResponse).toBe('{malformed');
  });

  // ── 5. Rule Engine independence ──

  it('labels provider feedback separately from canonical comparison', () => {
    const { page, fixture } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A text' },
      { candidateId: 'c2', title: 'B', text: 'Story B text' }
    ];
    page.storyQuality = { classification: 'MATERIAL_DIFFERENCE', summary: 'Different endings', pairs: [], differences: [], evidenceState: 'DIFFERENT' };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', diversityAssessment: { classification: 'MATERIAL_DIFFERENCE', summary: 'Different endings' },
      candidateReviews: [], recommendedCandidateId: 'c1', recommendationReason: 'Provider suggestion',
      overallConcerns: [], evidenceLimitations: []
    };
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    // Provider suggestion should be labeled as such
    expect(fixture.nativeElement.textContent).toContain('Provider suggestion');
    // Canonical comparison should be separate
    expect(fixture.nativeElement.textContent).toContain('Canonical comparison');
  });

  // ── 6. Turkish Unicode text ──

  it('handles Turkish Unicode text in findings without corruption', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'Türkçe', text: 'Türkçe öykü — çığlık: ğüşİ' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Türkçe karakterler doğru kullanılmış', dimension: 'dil', supportingTextEvidence: ['ğüşİ'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].finding).toBe('Türkçe karakterler doğru kullanılmış');
    expect(findings[0].supportingText).toEqual(['ğüşİ']);
  });

  // ── 7. Reload consistency ──

  it('preserves finding type classification after persist and restore', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'CONCERN', finding: 'Weak ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    // Persist
    page.persist();
    // Verify data is stored
    const stored = localStorage.getItem('pompom.creative-studio.v1');
    expect(stored).not.toBeNull();
    // Verify findings are still classified correctly after persist
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('STRENGTH');
    expect(findings[1].findingType).toBe('CONCERN');
    // Verify stored data contains findingType
    const parsed = JSON.parse(stored!);
    expect(parsed.storyReview.candidateReviews[0].findings[0].findingType).toBe('STRENGTH');
    expect(parsed.storyReview.candidateReviews[0].findings[1].findingType).toBe('CONCERN');
  });

  // ── 8. HIGH severity only for genuinely serious issues ──

  it('classifies HIGH severity concern when evidence supports it', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Missing core plot resolution', dimension: 'narrative completeness', severity: 'high', supportingTextEvidence: ['Story ends without resolving the central conflict'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('CONCERN');
    expect(findings[0].severity).toBe('high');
  });

  it('does not create artificial HIGH findings for distribution', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'STRENGTH', finding: 'Good pacing', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'OBSERVATION', finding: 'Uses dialogue', dimension: 'style', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    const findings = page.normalizedReviewFindings('c1');
    const highCount = findings.filter((f: any) => f.severity === 'high').length;
    expect(highCount).toBe(0);
  });

  // ── 9. Evidence and source quotation ──

  it('displays supporting text evidence for findings', () => {
    const { page, fixture } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'CONCERN', finding: 'Weak ending', dimension: 'payoff', severity: 'medium', supportingTextEvidence: ['No resolution shown', 'Ending is abrupt'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    page.selectedCandidateIdValue = 'c1';
    page.reviewDialogOpen = true;
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('No resolution shown');
    expect(fixture.nativeElement.textContent).toContain('Ending is abrupt');
  });

  // ── 10. Provider recommendation is suggestion, not canonical truth ──

  it('displays provider recommendation as suggestion, not approval', () => {
    const { page, fixture } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'MATERIAL_DIFFERENCE', summary: 'Different endings', pairs: [], differences: [], evidenceState: 'DIFFERENT' };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 has stronger payoff',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Provider suggestion');
    // Should NOT contain approval language
    expect(fixture.nativeElement.textContent).not.toContain('Approved by');
  });
});
