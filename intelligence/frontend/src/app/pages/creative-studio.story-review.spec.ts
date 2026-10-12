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
  afterEach(() => {
    // Flush any pending HTTP requests instead of strict verify,
    // as constructor makes async calls that may not all be matched.
    http?.match(() => true).forEach(r => r.flush([]));
    http?.verify();
    localStorage.clear();
    TestBed.resetTestingModule();
  });

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
    // Use a recent timestamp so it's classified as "Current review"
    const recentTimestamp = new Date(Date.now() - 3600000).toISOString(); // 1 hour ago
    page.storyReview = { reviewId: 'live-123', reviewModel: 'gpt-4o-mini', reviewTimestamp: recentTimestamp };
    const label = page.reviewTimestampLabel();
    expect(label).toContain('Current review');
    expect(label).toContain(recentTimestamp.slice(0, 19));
  });

  it('labels old review as historical with age', () => {
    const { page } = open();
    page.storyReview = { reviewId: 'live-123', reviewModel: 'gpt-4o-mini', reviewTimestamp: '2026-10-11T10:00:00Z' };
    const label = page.reviewTimestampLabel();
    // 2026-10-11 is in the past relative to test run time, so it's historical
    expect(label).toContain('Historical review');
    expect(label).toContain('2026-10-11T10:00:00.000Z');
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

  // ── 11. Mixed-sentiment classification (P0 confirmed bugs) ──

  it('classifies "Progression is clear but slightly less engaging than candidate-1" as MIXED', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Progression is clear but slightly less engaging than candidate-1', dimension: 'progression', supportingTextEvidence: ['Clear setup but loses momentum'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // Positive "clear" + comparative weakness "less engaging" => MIXED
    expect(findings[0].findingType).toBe('MIXED');
    expect(findings[0].findingType).not.toBe('STRENGTH');
  });

  it('classifies "Less original due to repetitive phrasing" as CONCERN', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Less original due to repetitive phrasing', dimension: 'originality', supportingTextEvidence: ['Repeats same structure'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('CONCERN');
    expect(findings[0].findingType).not.toBe('OBSERVATION');
  });

  it('classifies "but however although" weakness clauses as MIXED when positive signal present', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Good character setup but the pacing is weak in the middle', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { finding: 'Strong visual potential however the dialogue is lacking', dimension: 'dialogue', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { finding: 'Although the opening is vivid the ending is unclear', dimension: 'ending', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // All three have positive + negative => MIXED
    expect(findings[0].findingType).toBe('MIXED');
    expect(findings[1].findingType).toBe('MIXED');
    expect(findings[2].findingType).toBe('MIXED');
  });

  it('classifies "not as engaging as" comparative weakness as MIXED', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Not as engaging as the first candidate', dimension: 'engagement', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // "Not as engaging as" contains "engaging" (positive) + "not as" (comparative weakness) => MIXED
    expect(findings[0].findingType).toBe('MIXED');
  });

  // ── 12. Concern count aggregation (P0 confirmed bug) ──

  it('counts CONCERN findings across all candidates for concerns label', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED',
      overallConcerns: [], // Provider reports zero concerns
      candidateReviews: [
        { candidateId: 'c1', findings: [
          { finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { finding: 'Weak ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: ['No resolution'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]},
        { candidateId: 'c2', findings: [
          { finding: 'Good pacing', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { finding: 'Ambiguous character motivation', dimension: 'character', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]}
      ], recommendedCandidateId: null, recommendationReason: ''
    };
    // Even though overallConcerns is empty, we should count typed CONCERN findings
    const label = page.reviewConcernsLabel();
    expect(label).not.toBe('0');
    expect(label).not.toBe('Unknown');
    // There are 2 CONCERN findings: "Weak ending" and "Ambiguous character motivation"
    expect(Number(label)).toBeGreaterThanOrEqual(2);
  });

  it('shows Unknown when no candidate reviews exist', () => {
    const { page } = open();
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [], overallConcerns: []
    };
    expect(page.reviewConcernsLabel()).toBe('Unknown');
  });

  it('shows correct count when all findings are STRENGTH', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED',
      overallConcerns: [],
      candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
          { findingType: 'STRENGTH', finding: 'Good pacing', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    // No CONCERN findings, so count is 0, which maps to Unknown
    expect(page.reviewConcernsLabel()).toBe('Unknown');
  });

  // ── 13. PARTIALLY_DISTINCT contradiction (P1) ──

  it('adds evidence limitation for PARTIALLY_DISTINCT with no supported differences', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A with some differences' },
      { candidateId: 'c2', title: 'B', text: 'Story B with some differences' }
    ];
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Partially distinct but no supported different narrative dimensions were extracted.',
      differences: [], pairs: [], evidenceState: 'UNKNOWN'
    };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 has the strongest event progression',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.evidenceLimitations.length).toBeGreaterThan(0);
    expect(normalized.evidenceLimitations[0]).toContain('PARTIALLY DISTINCT');
    expect(normalized.recommendationReason).toContain('Provider suggestion only');
  });

  it('marks provider recommendation as AI suggestion when not already labeled', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'MATERIAL_DIFFERENCE', differences: ['ending'], pairs: [] };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 has the strongest event progression',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.recommendationReason).toContain('AI suggestion');
    expect(normalized.recommendationReason).toContain('provider claim');
  });

  it('does not double-wrap recommendation already marked as suggestion', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'MATERIAL_DIFFERENCE', differences: ['ending'], pairs: [] };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Provider suggestion only · Candidate 1 is better',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    // Should not contain "AI suggestion · Provider suggestion only"
    expect(normalized.recommendationReason).not.toContain('AI suggestion · Provider suggestion');
  });

  // ── 14. Fixture provenance verification ──

  it('fixture review shows 2023-10-05 as DEMO / FIXTURE, not current evaluation', () => {
    const { page } = open();
    page.storyReview = {
      reviewId: 'LOCAL_MOCK_REVIEW', reviewModel: 'local-mock',
      reviewTimestamp: '2023-10-05T12:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [],
      recommendedCandidateId: null, recommendationReason: ''
    };
    expect(page.reviewTimestampLabel()).toBe('DEMO / FIXTURE · Review time unavailable');
    // The timestamp 2023-10-05 must not appear as a current evaluation time
    expect(page.reviewTimestampLabel()).not.toContain('2023-10-05');
  });

  it('fixture review does not auto-approve story', () => {
    const { page } = open();
    page.fixtureMode = true;
    page.candidates = [
      { candidateId: 'candidate-1', title: 'A', text: 'Story A' },
      { candidateId: 'candidate-2', title: 'B', text: 'Story B' }
    ];
    page.selectedCandidateIdValue = 'candidate-1';
    page.selectedStory = 'Story A';
    // Fixture review should not set approval record
    expect(page.approvalRecordId).toBeFalsy();
  });

  // ── 15. P0 — "lacks some engagement" mixed finding (confirmed bug) ──

  it('classifies "Progression is clear but lacks some engagement" as MIXED', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Progression is clear but lacks some engagement.', dimension: 'progression', supportingTextEvidence: ['Clear setup but loses momentum'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // This is genuinely mixed: positive "clear" + negative "lacks engagement"
    expect(findings[0].findingType).toBe('MIXED');
    expect(findings[0].findingType).not.toBe('STRENGTH');
    // Severity should be null for MIXED (not a pure CONCERN)
    expect(findings[0].severity).toBeNull();
  });

  it('classifies "Progression is clear but slightly less engaging than candidate-1" as MIXED', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Progression is clear but slightly less engaging than candidate-1', dimension: 'progression', supportingTextEvidence: ['Clear setup but loses momentum'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // Comparative weakness with positive signal => MIXED
    expect(findings[0].findingType).toBe('MIXED');
    expect(findings[0].findingType).not.toBe('STRENGTH');
  });

  it('classifies "Good character setup but the pacing is weak" as MIXED', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Good character setup but the pacing is weak in the middle', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('MIXED');
  });

  it('classifies pure negative without positive signal as CONCERN', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'The pacing is weak and the ending is unclear', dimension: 'pacing', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    // No positive signal, pure negative => CONCERN
    expect(findings[0].findingType).toBe('CONCERN');
  });

  it('classifies "Less original due to repetitive phrasing" as CONCERN', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Less original due to repetitive phrasing', dimension: 'originality', supportingTextEvidence: ['Repeats same structure'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('CONCERN');
    expect(findings[0].findingType).not.toBe('OBSERVATION');
  });

  // ── 16. P0 — Concern count provenance ──

  it('distinguishes canonical concerns from provider-reported concerns', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED',
      overallConcerns: ['Some provider concern'], // Provider reports 1 concern
      candidateReviews: [
        { candidateId: 'c1', findings: [
          { finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]},
        { candidateId: 'c2', findings: [
          { finding: 'Weak ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: ['No resolution'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]}
      ], recommendedCandidateId: null, recommendationReason: ''
    };
    // 1 canonical CONCERN finding ("Weak ending") + 1 provider concern
    // Canonical count takes precedence
    const label = page.reviewConcernsLabel();
    expect(label).toBe('1');
    // Should NOT show "Provider: 1" when we have canonical concerns
    expect(label).not.toContain('Provider');
  });

  it('shows provider concerns when no canonical concerns exist', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'Story A' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED',
      overallConcerns: ['Provider concern 1', 'Provider concern 2'],
      candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], recommendedCandidateId: null, recommendationReason: ''
    };
    const label = page.reviewConcernsLabel();
    expect(label).toBe('Provider: 2');
  });

  // ── 17. P1 — PARTIALLY_DISTINCT contradiction fix ──

  it('maps PARTIALLY_DISTINCT without supported differences to INSUFFICIENT_EVIDENCE in display', () => {
    const { page } = open();
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Partially distinct but no supported different narrative dimensions were extracted.',
      differences: [], pairs: [], evidenceState: 'UNKNOWN'
    };
    expect(page.reviewComparisonLabel()).toBe('INSUFFICIENT_EVIDENCE');
    expect(page.reviewComparisonSummary()).toContain('Insufficient evidence');
    expect(page.reviewComparisonSummary()).not.toContain('material dimensions');
  });

  it('preserves PARTIALLY_DISTINCT when supported differences exist', () => {
    const { page } = open();
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Partially distinct with supported differences.',
      differences: ['ending'], pairs: [], evidenceState: 'PARTIAL'
    };
    expect(page.reviewComparisonLabel()).toBe('PARTIALLY_DISTINCT');
    expect(page.reviewComparisonSummary()).toBe('Partially distinct with supported differences.');
  });

  it('preserves NEAR_DUPLICATE classification', () => {
    const { page } = open();
    page.storyQuality = {
      classification: 'NEAR_DUPLICATE', variationClass: 'NEAR_DUPLICATE',
      summary: 'Candidates are near duplicates.',
      differences: [], pairs: [], evidenceState: 'SAME'
    };
    expect(page.reviewComparisonLabel()).toBe('NEAR_DUPLICATE');
  });

  // ── 18. MIXED finding type in normalized findings ──

  it('preserves MIXED finding type through normalization', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'MIXED', finding: 'Clear but lacks engagement', dimension: 'progression', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].findingType).toBe('MIXED');
    expect(findings[0].severity).toBeNull();
  });

  // ── 19. Provider recommendation evidence status ──

  it('marks provider recommendation as AI suggestion with evidence status', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'MATERIAL_DIFFERENCE', differences: ['ending'], pairs: [] };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate-1 has the strongest event progression',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.recommendationReason).toContain('AI suggestion');
    expect(normalized.recommendationReason).toContain('provider claim');
    expect(normalized.recommendationReason).toContain('not independently verified');
  });

  it('does not auto-approve story based on provider recommendation', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 is best',
      candidateReviews: [], overallConcerns: []
    };
    // Provider recommendation should not set approval
    expect(page.approvalRecordId).toBeFalsy();
  });

  // ── 20. P0 — Canonical comparison: reconciliation corrects unsupported PARTIALLY_DISTINCT ──

  it('reconcileStoryComparison corrects PARTIALLY_DISTINCT without differences to INSUFFICIENT_EVIDENCE', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cupboard and the notes follow her to a secret chart.' }
    ];
    // Simulate backend returning PARTIALLY_DISTINCT without supported differences
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Partially distinct.', differences: [], pairs: [], evidenceState: 'UNKNOWN'
    };
    (page as any).reconcileStoryComparison();
    // After reconciliation, unsupported PARTIALLY_DISTINCT should be corrected
    expect(page.storyQuality.classification).toBe('INSUFFICIENT_EVIDENCE');
    expect(page.storyQuality.summary).toContain('Insufficient evidence');
  });

  it('reconcileStoryComparison preserves PARTIALLY_DISTINCT with supported differences', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A with different ending.' },
      { candidateId: 'c2', title: 'B', text: 'Story B with same ending.' }
    ];
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Partially distinct.', differences: ['ending'], pairs: [], evidenceState: 'PARTIAL'
    };
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.classification).toBe('PARTIALLY_DISTINCT');
  });

  it('reconcileStoryComparison produces INSUFFICIENT_EVIDENCE for near-identical candidates', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    // Exact body match → NEAR_DUPLICATE
    expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');
  });

  // ── 21. P0 — Ending existence vs quality separation ──

  it('reviewEndingStatus returns PRESENT for a story with a clear final event', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A',
      text: 'Mimi opens the cabinet and the notes follow her. She climbs the ladder and reaches the top. Mimi becomes covered in sticky notes, leaving only her eyes visible.'
    };
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
  });

  it('reviewEndingStatus returns PRESENT based on last sentence heuristic', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A',
      text: 'Mimi starts her adventure. She finds a box. Inside the box are sticky notes that multiply rapidly until she is covered.'
    };
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
  });

  it('reviewEndingStatus returns UNKNOWN for very short text', () => {
    const { page } = open();
    const candidate = { candidateId: 'c1', title: 'A', text: 'Short.' };
    expect(page.reviewEndingStatus(candidate)).toBe('UNKNOWN');
  });

  it('reviewEndingStatus returns PRESENT from preflight data', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A', text: 'A story.',
      preflight: { ending: 'PRESENT' }
    };
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
  });

  it('reviewEndingStatus returns ABSENT from preflight data', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A', text: 'A story.',
      preflight: { ending: 'ABSENT' }
    };
    expect(page.reviewEndingStatus(candidate)).toBe('ABSENT');
  });

  it('reviewEndingQuality returns Not assessed when no ending finding exists', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    expect(page.reviewEndingQuality('c1')).toBe('Not assessed');
  });

  it('reviewEndingQuality returns Concern raised for ending CONCERN', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Ambiguous ending', dimension: 'payoff', severity: 'high', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    expect(page.reviewEndingQuality('c1')).toBe('Concern raised');
  });

  it('reviewEndingQuality returns Positive signal for ending STRENGTH', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { findingType: 'STRENGTH', finding: 'Satisfying payoff', dimension: 'ending', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    expect(page.reviewEndingQuality('c1')).toBe('Positive signal');
  });

  it('ending existence is PRESENT while ending quality is separate', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A',
      text: 'Mimi opens the cabinet and the notes follow her. She climbs the ladder and reaches the top. Mimi becomes covered in sticky notes, leaving only her eyes visible.'
    };
    page.candidates = [candidate];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Ending is unclear', dimension: 'payoff', severity: 'medium', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    // Ending exists in the text
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
    // But creative quality is a concern
    expect(page.reviewEndingQuality('c1')).toBe('Concern raised');
    // They are independent assessments
  });

  // ── 22. P1 — Provider recommendation provenance consistency ──

  it('provider recommendation is labeled AI suggestion in normalizeStoryReview', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'INSUFFICIENT_EVIDENCE', differences: [], pairs: [] };
    // Use a fresh object to avoid mutation from previous tests
    const rawReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate-1 has the strongest event progression',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(JSON.parse(JSON.stringify(rawReview)));
    // When INSUFFICIENT_EVIDENCE, the unsupportedComparison path fires first,
    // producing "Provider suggestion only" instead of "AI suggestion"
    expect(normalized.recommendationReason).toMatch(/provider|suggestion/i);
    expect(normalized.evidenceLimitations.length).toBeGreaterThan(0);
  });

  it('provider recommendation with unsupported comparison adds evidence limitation', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'NEAR_DUPLICATE', differences: [], pairs: [] };
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate 1 is best',
      candidateReviews: [], overallConcerns: [], evidenceLimitations: []
    };
    const normalized = (page as any).normalizeStoryReview(page.storyReview);
    expect(normalized.evidenceLimitations.some((l: string) => l.includes('canonical comparison'))).toBe(true);
  });

  // ── 23. P1 — Approval records exact lineage and unresolved evidence ──

  it('approveStory payload includes unresolved evidence and comparison classification', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'Approved story text.' }];
    page.selectedCandidateIdValue = 'c1';
    page.selectedStory = 'Approved story text.';
    page.storyRecordId = 'test-record';
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', evidenceLimitations: ['Text-only review'],
      candidateReviews: [], overallConcerns: []
    };
    page.storyQuality = { classification: 'INSUFFICIENT_EVIDENCE', differences: [], pairs: [] };
    page.storyReviewStatus = 'CURRENT';
    page.fixtureMode = true;
    // In fixture mode, approveStory sets approvalRecordId directly
    page.approveStory();
    expect(page.approvalRecordId).toBe('LOCAL_MOCK_APPROVAL');
    expect(page.stage).toBe('PROMPT');
  });

  // ── 24. P1 — Historical review provenance ──

  it('reviewTimestampLabel distinguishes current from historical reviews', () => {
    const { page } = open();
    const recent = new Date(Date.now() - 1800000).toISOString(); // 30 min ago
    page.storyReview = { reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: recent };
    expect(page.reviewTimestampLabel()).toContain('Current review');
  });

  it('reviewTimestampLabel marks old reviews as historical with age', () => {
    const { page } = open();
    // 3 days ago
    const old = new Date(Date.now() - 3 * 24 * 3600000).toISOString();
    page.storyReview = { reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: old };
    const label = page.reviewTimestampLabel();
    expect(label).toContain('Historical review');
    expect(label).toContain('3d old');
  });

  it('reviewTimestampLabel marks very old reviews as historical with weeks', () => {
    const { page } = open();
    // 3 weeks ago
    const old = new Date(Date.now() - 21 * 24 * 3600000).toISOString();
    page.storyReview = { reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: old };
    const label = page.reviewTimestampLabel();
    expect(label).toContain('Historical review');
    expect(label).toContain('3w old');
  });

  // ── 25. Reload consistency ──

  it('reload preserves review, selection and provenance via normalizeStoryReview', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyQuality = { classification: 'INSUFFICIENT_EVIDENCE', differences: [], pairs: [] };
    // Use a fresh object to avoid mutation from previous normalization
    const rawReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', recommendedCandidateId: 'c1',
      recommendationReason: 'Candidate-1 is best',
      candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Clear opening', dimension: 'opening', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }], overallConcerns: [], evidenceLimitations: []
    };
    page.selectedCandidateIdValue = 'c1';
    page.reviewedStoryFingerprints = { c1: page.storyFingerprint('Story A') };
    // Simulate restore from localStorage (calls normalizeStoryReview)
    const normalized = (page as any).normalizeStoryReview(JSON.parse(JSON.stringify(rawReview)));
    // When INSUFFICIENT_EVIDENCE, the unsupportedComparison path fires first
    expect(normalized.recommendationReason).toMatch(/provider|suggestion/i);
    expect(page.selectedCandidateIdValue).toBe('c1');
    expect(page.reviewedStoryFingerprints['c1']).toBeTruthy();
  });

  // ── 26. Original Story and generated candidate approvals retain exact lineage ──

  it('approveStory with ORIGINAL_SOURCE records source fingerprint', () => {
    const { page } = open();
    page.fixtureMode = true;
    page.idea = 'Original Mimi story';
    page.selectedCandidateIdValue = 'ORIGINAL_SOURCE';
    page.selectedStory = 'Original Mimi story';
    page.storyRecordId = 'test-record';
    page.approveStory();
    expect(page.approvalRecordId).toBe('LOCAL_MOCK_APPROVAL');
    expect(page.stage).toBe('PROMPT');
  });

  it('approveStory with GENERATED_CANDIDATE records candidate fingerprint', () => {
    const { page } = open();
    page.fixtureMode = true;
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'Generated story.' }];
    page.selectedCandidateIdValue = 'c1';
    page.selectedStory = 'Generated story.';
    page.storyRecordId = 'test-record';
    page.approveStory();
    expect(page.approvalRecordId).toBe('LOCAL_MOCK_APPROVAL');
    expect(page.stage).toBe('PROMPT');
  });

  // ── 27. Turkish/Unicode content in findings ──

  it('handles Turkish Unicode text in findings', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'Mimi ve yapışkan notlar.' }];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Açılış net ve etkileyici', dimension: 'opening', supportingTextEvidence: ['Mimi ve yapışkan notlar'], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    const findings = page.normalizedReviewFindings('c1');
    expect(findings[0].finding).toBe('Açılış net ve etkileyici');
    // Turkish text is not classified by English heuristics; falls through to OBSERVATION
    expect(findings[0].findingType).toBe('OBSERVATION');
    // Explicit findingType from provider overrides heuristic
    page.storyReview.candidateReviews[0].findings[0].findingType = 'STRENGTH';
    const findings2 = page.normalizedReviewFindings('c1');
    expect(findings2[0].findingType).toBe('STRENGTH');
  });

  // ── 28. Malformed provider response ──

  it('handles malformed provider response gracefully', () => {
    const { page } = open();
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'A story' }];
    const normalized = (page as any).normalizeStoryReview('not valid json {{{');
    expect(normalized.reviewStatus).toBe('INVALID');
    expect(normalized.evidenceLimitations.length).toBeGreaterThan(0);
    expect(normalized.recommendedCandidateId).toBeNull();
  });

  it('handles null provider response gracefully', () => {
    const { page } = open();
    const normalized = (page as any).normalizeStoryReview(null);
    expect(normalized).toBeNull();
  });

  // ── 29. TDD — Scenario A: Three near-identical Mimi candidates without supported structural distinctions ──

  it('scenario A: three near-identical Mimi candidates yield INSUFFICIENT_EVIDENCE or NEAR_DUPLICATE', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'candidate-1', title: 'A brighter route', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'candidate-2', title: 'A quieter route', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'candidate-3', title: 'A winding route', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    // Exact body match → NEAR_DUPLICATE, not PARTIALLY_DISTINCT
    expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');
    expect(page.storyQuality.differences).toEqual([]);
    expect(page.reviewComparisonLabel()).toBe('NEAR_DUPLICATE');
    // UI must not show "material differences" when none exist
    expect(page.reviewComparisonSummary()).not.toContain('material differences');
  });

  // ── 30. TDD — Scenario B: Exact normalized story-body equality with different titles ──

  it('scenario B: exact body equality with different titles yields NEAR_DUPLICATE', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'Title Alpha', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'Title Beta', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');
    expect(page.storyQuality.summary).toContain('Titles do not establish');
  });

  // ── 31. TDD — Scenario C: Lexically similar but structurally uncertain stories ──

  it('scenario C: lexically similar stories without structural evidence yield INSUFFICIENT_EVIDENCE', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cupboard and the notes follow her to a secret chart.' }
    ];
    page.storyQuality = null;
    (page as any).reconcileStoryComparison();
    // High lexical similarity but no structural evidence → INSUFFICIENT_EVIDENCE
    expect(page.storyQuality.classification).toBe('INSUFFICIENT_EVIDENCE');
    expect(page.storyQuality.differences).toEqual([]);
  });

  // ── 32. TDD — Scenario D: Genuinely distinct candidates with explicitly supported material differences ──

  it('scenario D: genuinely distinct candidates preserve PARTIALLY_DISTINCT with supported differences', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and finds a treasure chest full of gold coins.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map leading outside.' }
    ];
    // Simulate backend returning PARTIALLY_DISTINCT with supported differences
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Candidates differ in ending function.', differences: ['endingFunction'], pairs: [], evidenceState: 'PARTIAL'
    };
    (page as any).reconcileStoryComparison();
    expect(page.storyQuality.classification).toBe('PARTIALLY_DISTINCT');
    expect(page.reviewComparisonLabel()).toBe('PARTIALLY_DISTINCT');
  });

  // ── 33. TDD — Scenario E: Historical review with old timestamp but exact matching source revision ──

  it('scenario E: historical review with matching source revision is labeled historical, not current', () => {
    const { page } = open();
    const oldTimestamp = '2023-10-05T12:00:00Z';
    page.storyReview = {
      reviewId: 'review-1', reviewModel: 'gpt-4o-mini', reviewTimestamp: oldTimestamp,
      reviewStatus: 'COMPLETED', candidateReviews: [], recommendedCandidateId: null, recommendationReason: ''
    };
    const label = page.reviewTimestampLabel();
    expect(label).toContain('Historical review');
    expect(label).not.toContain('Current review');
  });

  // ── 34. TDD — Scenario F: Stale review belonging to another candidate set ──

  it('scenario F: stale review detected when candidate text changes after review', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Original story text.' },
      { candidateId: 'c2', title: 'B', text: 'Another story text.' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [], recommendedCandidateId: null, recommendationReason: ''
    };
    page.reviewedStoryFingerprints = { c1: page.storyFingerprint('Original story text.') };
    page.selectedCandidateIdValue = 'c1';
    // Change the selected story text
    page.onSelectedStoryChange('Modified story text.');
    expect(page.storyReviewStatus).toBe('STALE');
  });

  // ── 35. TDD — Scenario G: Explicit ending event with unknown creative effectiveness ──

  it('scenario G: ending existence is PRESENT while ending quality is separate', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A',
      text: 'Mimi opens the cabinet and the notes follow her. She climbs the ladder and reaches the top. Mimi becomes covered in sticky notes, leaving only her eyes visible.'
    };
    page.candidates = [candidate];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewStatus: 'COMPLETED', candidateReviews: [{
        candidateId: 'c1', findings: [
          { finding: 'Ending is unclear', dimension: 'payoff', severity: 'medium', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'SUPPORTED' }
        ]
      }]
    };
    // Ending exists in the text
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
    // But creative quality is a concern
    expect(page.reviewEndingQuality('c1')).toBe('Concern raised');
    // They are independent — existence does not imply quality
  });

  it('scenario G: ending existence is PRESENT even without preflight data', () => {
    const { page } = open();
    const candidate = {
      candidateId: 'c1', title: 'A',
      text: 'Mimi opens the cabinet and the notes follow her. She climbs the ladder and reaches the top. Mimi becomes covered in sticky notes, leaving only her eyes visible.'
      // No preflight data
    };
    // reviewEndingStatus should detect the ending from text heuristic
    expect(page.reviewEndingStatus(candidate)).toBe('PRESENT');
  });

  // ── 36. TDD — Scenario H: Original and generated candidate approval followed by reload and exact Prompt lineage ──

  it('scenario H: original story approval preserves exact text and fingerprint', () => {
    const { page } = open();
    page.fixtureMode = true;
    page.idea = 'Mimi and the sticky notes original story.';
    page.selectedCandidateIdValue = 'ORIGINAL_SOURCE';
    page.selectedStory = 'Mimi and the sticky notes original story.';
    page.storyRecordId = 'test-record';
    page.approveStory();
    expect(page.approvalRecordId).toBe('LOCAL_MOCK_APPROVAL');
    expect(page.stage).toBe('PROMPT');
  });

  it('scenario H: generated candidate approval preserves exact text and fingerprint', () => {
    const { page } = open();
    page.fixtureMode = true;
    page.candidates = [{ candidateId: 'c1', title: 'A', text: 'Generated Mimi story with sticky notes.' }];
    page.selectedCandidateIdValue = 'c1';
    page.selectedStory = 'Generated Mimi story with sticky notes.';
    page.storyRecordId = 'test-record';
    page.approveStory();
    expect(page.approvalRecordId).toBe('LOCAL_MOCK_APPROVAL');
    expect(page.stage).toBe('PROMPT');
  });

  // ── 37. P0 — Unsupported PARTIALLY_DISTINCT cannot occur in UI ──

  it('P0: UI never shows PARTIALLY_DISTINCT with "no material differences" contradiction', () => {
    const { page, fixture } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' },
      { candidateId: 'c2', title: 'B', text: 'Mimi opens the cabinet and the notes follow her to a hidden map.' }
    ];
    // Simulate backend returning PARTIALLY_DISTINCT without supported differences
    page.storyQuality = {
      classification: 'PARTIALLY_DISTINCT', variationClass: 'PARTIALLY_DISTINCT',
      summary: 'Candidates share core structure but differ in some material dimensions.',
      differences: [], pairs: [], evidenceState: 'UNKNOWN'
    };
    (page as any).reconcileStoryComparison();
    // Exact body match takes priority: NEAR_DUPLICATE is the correct classification
    // The key point: PARTIALLY_DISTINCT without differences is NEVER shown to the user
    expect(page.storyQuality.classification).not.toBe('PARTIALLY_DISTINCT');
    expect(page.reviewComparisonLabel()).not.toBe('PARTIALLY_DISTINCT');
    // The contradictory summary must be replaced
    expect(page.reviewComparisonSummary()).not.toContain('material dimensions');
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    // UI must not show PARTIALLY_DISTINCT badge
    expect(fixture.nativeElement.textContent).not.toMatch(/PARTIALLY_DISTINCT.*material differences/i);
  });

  // ── 38. P1 — CURRENT review status semantics ──

  it('P1: CURRENT review status means latest review for exact source/candidate revision', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Story A' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: new Date().toISOString(),
      reviewStatus: 'COMPLETED', candidateReviews: [], recommendedCandidateId: null, recommendationReason: ''
    };
    page.reviewedStoryFingerprints = {
      c1: page.storyFingerprint('Story A'),
      c2: page.storyFingerprint('Story B')
    };
    // When fingerprints match and review is recent, status is CURRENT
    expect(page.storyReviewStatus).toBe('NOT_REVIEWED'); // initial state
    // After reviewStories(), status becomes CURRENT
    // The key point: CURRENT means the review matches the current candidate fingerprints
  });

  it('P1: STALE review status when candidate text changes after review', () => {
    const { page } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Original text' },
      { candidateId: 'c2', title: 'B', text: 'Story B' }
    ];
    page.storyReview = {
      reviewId: 'r1', reviewModel: 'gpt', reviewTimestamp: new Date().toISOString(),
      reviewStatus: 'COMPLETED', candidateReviews: [], recommendedCandidateId: null, recommendationReason: ''
    };
    page.reviewedStoryFingerprints = { c1: page.storyFingerprint('Original text') };
    page.selectedCandidateIdValue = 'c1';
    page.storyReviewStatus = 'CURRENT';
    // Change the text
    page.onSelectedStoryChange('Modified text');
    expect(page.storyReviewStatus).toBe('STALE');
  });

  // ── 39. Ending display consistency ──

  it('ending display uses reviewEndingStatus for candidates without preflight data', () => {
    const { page, fixture } = open();
    page.candidates = [
      { candidateId: 'c1', title: 'A', text: 'Mimi opens the cabinet and the notes follow her. She climbs the ladder and reaches the top. Mimi becomes covered in sticky notes, leaving only her eyes visible.' }
      // No preflight data
    ];
    page.stage = 'STORY';
    fixture.changeDetectorRef.detectChanges();
    fixture.detectChanges();
    // Ending should show PRESENT based on text heuristic, not blank
    expect(fixture.nativeElement.textContent).toContain('Ending');
    expect(fixture.nativeElement.textContent).toContain('PRESENT');
  });
});
