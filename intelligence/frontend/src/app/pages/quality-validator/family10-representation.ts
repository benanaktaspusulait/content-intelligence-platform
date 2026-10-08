export type GeneralProducibilityStatus = 'PRODUCIBLE' | 'RISKY' | 'NOT_PRODUCIBLE' | 'UNKNOWN' | 'NOT_APPLICABLE';
export type ProductionRiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'UNKNOWN' | 'NOT_APPLICABLE';
export interface ProductionRisk {
  level: ProductionRiskLevel;
  reason: string;
  evidenceReferences: string[];
  material: boolean;
  requiresRedesign: boolean;
}
export interface GeneralProducibility {
  status: GeneralProducibilityStatus;
  dimensions: Record<string, ProductionRisk>;
  reasons: string[];
  materialRisks: string[];
  unknownDimensions: string[];
  durationSeconds: number | null;
  durationSource: string;
  durationLoad: ProductionRisk & { dependentStateChanges: number | null; changesPerSecond: number | null };
  provenance: {
    evaluatorVersion?: string;
    source?: string;
    sourceEvidence?: { source?: string; promptHash?: string; fixtureVersion?: string; evidenceReferences?: string[] };
    [key: string]: unknown;
  };
}
/** Sort material risks first without rewriting canonical status, reasons or nulls. */
export function generalProducibilityRows(value: GeneralProducibility | null | undefined): Array<ProductionRisk & { key: string }> {
  if (!value) return [];
  const rank: Record<ProductionRiskLevel, number> = { HIGH: 0, MODERATE: 1, UNKNOWN: 2, LOW: 3, NOT_APPLICABLE: 4 };
  return Object.entries(value.dimensions).map(([key, risk]) => ({ key, ...risk }))
    .sort((a, b) => Number(b.material) - Number(a.material) || rank[a.level] - rank[b.level]);
}
