import { enabledPublicationPlatforms, isPublicationPlatformEnabled } from './operations.page';

describe('Operations publication safety', () => {
  it('exposes only non-Meta platforms while Meta publishing is disabled', () => {
    expect(enabledPublicationPlatforms).toEqual(['TIKTOK', 'YOUTUBE']);
    expect(isPublicationPlatformEnabled('FACEBOOK')).toBe(false);
    expect(isPublicationPlatformEnabled('INSTAGRAM')).toBe(false);
    expect(isPublicationPlatformEnabled('TIKTOK')).toBe(true);
    expect(isPublicationPlatformEnabled('YOUTUBE')).toBe(true);
  });
});
