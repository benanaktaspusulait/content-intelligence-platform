export interface SpecializedApplicability {
  status: 'APPLICABLE' | 'NOT_APPLICABLE' | 'UNKNOWN';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  evidenceReferences: string[];
  reason: string;
}

export const SPECIALIZED_APPLICABILITY_RULE_IDS = [
  'STUBBORN_RETURN_LOOP',
  'STUBBORN_RETURN_HOOK',
  'STUBBORN_RETURN_PAYOFF',
] as const;

export interface SpecializedApplicabilityRow extends SpecializedApplicability {
  ruleId: string;
}

export function toSpecializedApplicabilityRows(
  value: Record<string, SpecializedApplicability> | null | undefined,
): SpecializedApplicabilityRow[] {
  return SPECIALIZED_APPLICABILITY_RULE_IDS.map(ruleId => ({
    ruleId,
    ...(value?.[ruleId] ?? {
      status: 'UNKNOWN' as const,
      confidence: 'LOW' as const,
      evidenceReferences: [],
      reason: 'Applicability evidence is unavailable.',
    }),
  }));
}
