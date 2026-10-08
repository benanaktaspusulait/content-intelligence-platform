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

export interface CreativeGradeSources {
  /** Legacy grade is accepted for shape compatibility but intentionally ignored. */
  grade?: string | null;
  family8?: {
    creativeQuality?: {
      creativeGrade?: string | null;
    } | null;
  } | null;
  creative_grade?: string | null;
}

export function formatCreativeGrade(assessment: CreativeGradeSources | null | undefined): string {
  const family8Grade = assessment?.family8?.creativeQuality?.creativeGrade?.trim();
  if (family8Grade) return family8Grade;

  const canonicalGrade = assessment?.creative_grade?.trim();
  return canonicalGrade || 'N/A';
}

export function formatReadiness(
  promptStage: string | null | undefined,
  legacyReadiness: string | null | undefined,
): string {
  const readiness = promptStage?.trim() || legacyReadiness?.trim();
  return readiness ? readiness.replaceAll('_', ' ') : 'N/A';
}

export function formatAuthorizationReason<T extends AuthorizationReasonPresentation>(reason: T): T {
  return { ...reason };
}
