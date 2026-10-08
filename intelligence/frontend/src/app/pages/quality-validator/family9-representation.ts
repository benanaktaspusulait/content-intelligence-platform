export type EvaluationCoverageUnit = 'RATIO' | 'PERCENT';

export interface AuthorizationReasonPresentation {
  status: string;
  source: string;
  message: string;
  references: string[];
  [key: string]: unknown;
}

export function formatNullableScore(score: number | null | undefined): string {
  return score == null ? 'N/A' : score.toFixed(1);
}

export function formatEvaluationCoverage(
  value: number | null | undefined,
  unit: EvaluationCoverageUnit,
): string {
  if (value == null) return 'N/A';
  const percent = unit === 'RATIO' ? value * 100 : value;
  return `${percent.toFixed(0)}%`;
}

export function formatAuthorizationReason<T extends AuthorizationReasonPresentation>(reason: T): T {
  return { ...reason };
}
