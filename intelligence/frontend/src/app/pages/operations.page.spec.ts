import { enabledPublicationPlatforms, isPublicationPlatformEnabled, isPublicationCancellable, isScheduleCancellable } from './operations.page';

describe('Operations publication safety', () => {
  it('exposes only non-Meta platforms while Meta publishing is disabled', () => {
    expect(enabledPublicationPlatforms).toEqual(['TIKTOK', 'YOUTUBE']);
    expect(isPublicationPlatformEnabled('FACEBOOK')).toBe(false);
    expect(isPublicationPlatformEnabled('INSTAGRAM')).toBe(false);
    expect(isPublicationPlatformEnabled('TIKTOK')).toBe(true);
    expect(isPublicationPlatformEnabled('YOUTUBE')).toBe(true);
  });

  it('allows cancellation only for active publication states', () => {
    expect(isPublicationCancellable('QUEUED')).toBe(true);
    expect(isPublicationCancellable('PROCESSING')).toBe(true);
    expect(isPublicationCancellable('COMPLETED')).toBe(false);
    expect(isPublicationCancellable('FAILED')).toBe(false);
  });

  it('allows schedule cancellation until terminal state', () => {
    expect(isScheduleCancellable('SCHEDULED')).toBe(true);
    expect(isScheduleCancellable('COMPLETED')).toBe(false);
    expect(isScheduleCancellable('CANCELLED')).toBe(false);
  });
});
