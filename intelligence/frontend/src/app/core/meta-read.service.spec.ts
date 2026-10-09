import { MetaReadService } from './meta-read.service';

describe('MetaReadService', () => {
  it('uses bounded reconciliation endpoint with an explicit limit', () => {
    const post = vi.fn(() => ({ subscribe: vi.fn() }));
    const http = { post };
    const service = new MetaReadService(http as any);
    service.reconcileComments(25);
    expect(http.post).toHaveBeenCalledWith('/api/v1/meta/comments/reconcile', {}, { params: expect.anything() });
    const options = (post.mock.calls as any[])[0][2];
    expect(options.params.get('limit')).toBe('25');
  });
});
