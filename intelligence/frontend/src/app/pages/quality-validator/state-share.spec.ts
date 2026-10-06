import {
  clampPercent,
  formatStateShare,
  isStateShareDanger,
  isStateShareWarning,
  maxStateShare,
} from './state-share';

describe('visual state share', () => {
  // What the API sends for a 15s video with beats of 0.8s, 2.2s, 3s, 3s, 3s, 2s and 1s.
  const apiPercentages = [5.333333333333334, 14.666666666666666, 20, 20, 20, 13.333333333333334, 6.666666666666667];

  it('treats the API value as percent and does not multiply it by 100 again', () => {
    expect(apiPercentages.map(formatStateShare)).toEqual(['5.3%', '14.7%', '20.0%', '20.0%', '20.0%', '13.3%', '6.7%']);
  });

  it('reports the max state as the largest share (20%), not a 100x multiple (2000%)', () => {
    const max = maxStateShare(apiPercentages.map(percentage => ({ percentage })));
    expect(max).toBe(20);
    expect(formatStateShare(max)).toBe('20.0%');
  });

  it('never renders a share above 100% or below 0%', () => {
    expect(formatStateShare(2000)).toBe('100.0%');
    expect(formatStateShare(-5)).toBe('0.0%');
    expect(clampPercent(Number.NaN)).toBe(0);
  });

  it('uses percent-unit thresholds for warning (25) and danger (30)', () => {
    expect(isStateShareWarning(20)).toBe(false);
    expect(isStateShareWarning(26)).toBe(true);
    expect(isStateShareDanger(30)).toBe(false);
    expect(isStateShareDanger(31)).toBe(true);
    // A 0-1 ratio mistaken for percent would wrongly look safe; the helper never receives one.
    expect(isStateShareDanger(0.5)).toBe(false);
  });
});
