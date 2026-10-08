import {
  formatAuthorizationReason,
  formatEvaluationCoverage,
  formatNullableScore,
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
});
