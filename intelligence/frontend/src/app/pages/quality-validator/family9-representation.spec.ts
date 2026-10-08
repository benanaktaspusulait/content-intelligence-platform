import {
  formatAuthorizationReason,
  formatCreativeGrade,
  formatEvaluationCoverage,
  formatNullableScore,
  formatReadiness,
} from './family9-representation';

describe('Family 9 representation consistency', () => {
  it('renders nullable scores as N/A without changing numeric scores', () => {
    expect(formatNullableScore(null)).toBe('N/A');
    expect(formatNullableScore(82.5)).toBe('82.5');
  });

  it('renders a canonical ratio and an already-percent value as 75% exactly once', () => {
    expect(formatEvaluationCoverage(0.75, 'RATIO')).toBe('75%');
    expect(formatEvaluationCoverage(75, 'PERCENT')).toBe('75%');
    expect(formatEvaluationCoverage(0.75, 'RATIO')).not.toContain('7500');
  });

  it('keeps blocked authorization status and reason evidence visible', () => {
    const formatted = formatAuthorizationReason({
      status: 'BLOCKED_PENDING_EVIDENCE',
      source: 'EVIDENCE_COMPLETENESS',
      message: 'Visual evidence pending',
      references: ['first-frame', 'silhouette'],
    });

    expect(formatted).toEqual({
      status: 'BLOCKED_PENDING_EVIDENCE',
      source: 'EVIDENCE_COMPLETENESS',
      message: 'Visual evidence pending',
      references: ['first-frame', 'silhouette'],
    });
    expect(formatted.status).not.toBe('Ready');
    expect(formatted.status).not.toBe('Failed');
    expect(formatted.source).toBe('EVIDENCE_COMPLETENESS');
    expect(formatted.message).toBe('Visual evidence pending');
    expect(formatted.references).toEqual(['first-frame', 'silhouette']);
  });

  it('prefers Family 8 creative grade, then canonical grade, and never legacy grade', () => {
    expect(formatCreativeGrade({
      family8: { creativeQuality: { creativeGrade: 'A' } },
      creative_grade: 'B',
    })).toBe('A');
    expect(formatCreativeGrade({
      family8: { creativeQuality: { creativeGrade: null } },
      creative_grade: 'B',
    })).toBe('B');
    expect(formatCreativeGrade({ grade: 'A' })).toBe('N/A');
    expect(formatCreativeGrade(undefined)).toBe('N/A');
  });

  it('formats prompt stage or legacy readiness safely without mixing canonical axes', () => {
    expect(formatReadiness('BLOCKED_PENDING_EVIDENCE', 'READY_TO_RENDER')).toBe('BLOCKED PENDING EVIDENCE');
    expect(formatReadiness(undefined, 'READY_TO_RENDER')).toBe('READY TO RENDER');
    expect(formatReadiness(undefined, undefined)).toBe('N/A');
    expect(formatReadiness('', '')).toBe('N/A');
  });
});
