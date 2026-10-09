import { vi } from 'vitest';
import { QualityValidatorComponent } from './quality-validator.component';

describe('accepted repair route', () => {
  it('carries the durable session explicitly when Router has not observed history.replaceState', () => {
    const page = Object.create(QualityValidatorComponent.prototype);
    page.router = { navigate: vi.fn() };
    page.setPromptText = vi.fn();
    page.useAcceptedRepair({ contentId: 1, promptVersionId: 2, rawText: 'Best candidate', repairSessionId: 'durable-session' });
    expect(page.router.navigate).toHaveBeenCalledWith(['/quality/detail'], {
      queryParams: { contentId: '1', promptVersionId: '2', repairSessionId: 'durable-session' },
      replaceUrl: true, queryParamsHandling: 'merge',
    });
    expect(page.setPromptText).toHaveBeenCalledWith('Best candidate');
  });
});
