import { vi } from 'vitest';
import { QualityValidatorComponent } from './quality-validator.component';

describe('accepted repair route', () => {
  it('carries the durable session explicitly when Router has not observed history.replaceState', () => {
    const page = Object.create(QualityValidatorComponent.prototype);
    page.router = { navigate: vi.fn() };
    page.setPromptText = vi.fn();
    page.useAcceptedRepair({ contentId: 1, promptVersionId: 2, rawText: 'Best candidate', repairSessionId: 'durable-session' });
    expect(page.router.navigate).toHaveBeenCalledWith(['/quality/detail'], {
      queryParams: { contentId: '1', promptVersionId: '2', repairSessionId: 'durable-session', repairAnalysisId: null, stage: 3 },
      replaceUrl: true, queryParamsHandling: 'merge',
    });
    expect(page.setPromptText).toHaveBeenCalledWith('Best candidate');
  });
});

describe('repair stage navigation from the conditional editor', () => {
  it('mounts the workflow before selecting Repair, without requiring a passing verdict', () => {
    const page = Object.create(QualityValidatorComponent.prototype);
    page.studioStage = 3;
    const child = {selectStage: vi.fn()};
    page.changeDetector = {detectChanges: vi.fn(() => { page.postFamilyWorkflow = child; })};
    page.scrollToQualityStep('priority-fixes');
    expect(page.studioStage).toBe(6);
    expect(page.changeDetector.detectChanges).toHaveBeenCalled();
    expect(child.selectStage).toHaveBeenCalledWith(6);
  });
  it('keeps the persisted BLOCKED analysis identity when opening Repair', () => {
    const page = Object.create(QualityValidatorComponent.prototype);
    page.studioMode=false;page.report={status:'BLOCKED'};page.validationRecordId=19;page.contentId='13';page.promptVersionId='21';
    page.scrollToQualityStep=vi.fn();page.router={navigate:vi.fn().mockResolvedValue(true)};
    page.continueToRepair();
    expect(page.scrollToQualityStep).toHaveBeenCalledWith('priority-fixes');
    expect(page.router.navigate).toHaveBeenCalledWith([],expect.objectContaining({queryParams:{studio:1,stage:6,repairAnalysisId:19}}));
    expect(page.validationRecordId).toBe(19);
    expect(page.studioMode).toBe(true);
  });
});
