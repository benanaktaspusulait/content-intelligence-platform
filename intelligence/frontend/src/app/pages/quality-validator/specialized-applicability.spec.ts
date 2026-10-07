import { toSpecializedApplicabilityRows } from './specialized-applicability';

describe('specialized applicability rows', () => {
  it('keeps the three specialized rule rows and preserves statuses losslessly', () => {
    const rows = toSpecializedApplicabilityRows({
      STUBBORN_RETURN_LOOP: { status: 'APPLICABLE', confidence: 'HIGH', evidenceReferences: ['beat_1'], reason: 'Box reclaim' },
      STUBBORN_RETURN_HOOK: { status: 'UNKNOWN', confidence: 'MEDIUM', evidenceReferences: [], reason: 'Threat unresolved' },
      STUBBORN_RETURN_PAYOFF: { status: 'NOT_APPLICABLE', confidence: 'HIGH', evidenceReferences: [], reason: 'Outside payoff domain' },
    });

    expect(rows.map(row => row.ruleId)).toEqual([
      'STUBBORN_RETURN_LOOP',
      'STUBBORN_RETURN_HOOK',
      'STUBBORN_RETURN_PAYOFF',
    ]);
    expect(rows.map(row => row.status)).toEqual(['APPLICABLE', 'UNKNOWN', 'NOT_APPLICABLE']);
    expect(rows[0]).toEqual({
      ruleId: 'STUBBORN_RETURN_LOOP',
      status: 'APPLICABLE',
      confidence: 'HIGH',
      evidenceReferences: ['beat_1'],
      reason: 'Box reclaim',
    });
  });

  it('uses neutral rows when applicability evidence is missing', () => {
    expect(toSpecializedApplicabilityRows(undefined)).toEqual([
      {
        ruleId: 'STUBBORN_RETURN_LOOP',
        status: 'UNKNOWN',
        confidence: 'LOW',
        evidenceReferences: [],
        reason: 'Applicability evidence is unavailable.',
      },
      {
        ruleId: 'STUBBORN_RETURN_HOOK',
        status: 'UNKNOWN',
        confidence: 'LOW',
        evidenceReferences: [],
        reason: 'Applicability evidence is unavailable.',
      },
      {
        ruleId: 'STUBBORN_RETURN_PAYOFF',
        status: 'UNKNOWN',
        confidence: 'LOW',
        evidenceReferences: [],
        reason: 'Applicability evidence is unavailable.',
      },
    ]);
  });
});
