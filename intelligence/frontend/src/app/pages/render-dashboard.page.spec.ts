import { RenderPreparationPage } from './render-preparation.page';

describe('Render Preparation workflow gates', () => {
  function page() {
    const http = { post: vi.fn() };
    const route = {} as any;
    return { component: new RenderPreparationPage(http as any, route, {} as any), http };
  }

  it('does not queue from the context-free render route', () => {
    const { component, http } = page();
    component.queueContentId.set('8');
    component.queuePromptVersionId.set('8');
    component.queueValidationId.set('12');
    component.queueRender();
    expect(component.queueError()).toContain('matching saved Quality Analysis');
    expect(http.post).not.toHaveBeenCalled();
  });

  it('keeps video queue closed until the exact saved review is authorized', () => {
    const { component, http } = page();
    component.workflowReviewId = 'review-8';
    component.workflowReview = { family8: { renderAuthorization: { status: 'BLOCKED_PENDING_EVIDENCE' } } };
    component.queueContentId.set('8');
    component.queuePromptVersionId.set('8');
    component.queueValidationId.set('12');
    component.queueRender();
    expect(component.queueError()).toContain('canonical authorization');
    expect(http.post).not.toHaveBeenCalled();
  });

  it('requires exact content, immutable prompt version, and analysis identity', () => {
    const { component } = page();
    component.queueContentId.set('7');
    component.queuePromptVersionId.set('8');
    component.analysisId = 'review-7-8';
    expect(component.workflowIdentityMatches({ contentId: 7, promptVersionId: 8, recordId: 'review-7-8' })).toBe(true);
    expect(component.workflowIdentityMatches({ contentId: 7, promptVersionId: 8, recordId: 'review-7-9' })).toBe(false);
    expect(component.workflowIdentityMatches({ contentId: 7, promptVersionId: 9, recordId: 'review-7-8' })).toBe(false);
    expect(component.workflowIdentityMatches({ contentId: 6, promptVersionId: 8, recordId: 'review-7-8' })).toBe(false);
  });

  it('never turns a FIRST_FRAME job into an implicit paid generation request', () => {
    const { component, http } = page();
    component.workflowReviewId = 'review-8';
    component.workflowReview = { family8: { renderAuthorization: { status: 'AUTHORIZED' } } };
    component.queueJobType.set('FIRST_FRAME');
    component.queueRender();
    expect(component.queueError()).toContain('explicit paid-call authorization');
    expect(http.post).not.toHaveBeenCalled();
  });
});
