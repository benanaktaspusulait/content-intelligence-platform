/**
 * Visual-state share helpers shared by the quality-validator components.
 *
 * Contract: the API returns `percentage` as a PERCENT of the timeline (0-100), e.g. 0.8s of a
 * 15s video is 5.33. It is NOT a 0-1 ratio, so it must never be multiplied by 100 again and
 * every threshold below is expressed in percent units.
 */
export const STATE_SHARE_WARNING_PERCENT = 25;
export const STATE_SHARE_DANGER_PERCENT = 30;

/** A share of the timeline can never be below 0% or above 100%. */
export function clampPercent(percent: number): number {
  if (!Number.isFinite(percent)) return 0;
  return Math.min(100, Math.max(0, percent));
}

export function formatStateShare(percent: number): string {
  return `${clampPercent(percent).toFixed(1)}%`;
}

export function maxStateShare(segments: ReadonlyArray<{ percentage: number }>): number {
  return segments.reduce((max, segment) => Math.max(max, clampPercent(segment.percentage)), 0);
}

export function isStateShareWarning(percent: number): boolean {
  return percent > STATE_SHARE_WARNING_PERCENT;
}

export function isStateShareDanger(percent: number): boolean {
  return percent > STATE_SHARE_DANGER_PERCENT;
}
