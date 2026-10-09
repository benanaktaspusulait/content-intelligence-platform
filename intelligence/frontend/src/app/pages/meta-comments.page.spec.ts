import { of } from 'rxjs';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MetaReadService } from '../core/meta-read.service';
import { MetaCommentsPage } from './meta-comments.page';

describe('MetaCommentsPage', () => {
  it('renders operational status and reconciliation control', async () => {
    await TestBed.configureTestingModule({
      imports: [MetaCommentsPage],
      providers: [provideRouter([]), { provide: MetaReadService, useValue: {
        listComments: () => of([]),
        getOperationsStatus: () => of({ health: 'UP', commentReplyEnabled: false, commentCount: 0, pendingWebhookCount: 2 }),
        reconcileComments: () => of({ processed: 2 }),
      }}],
    }).compileComponents();
    const fixture = TestBed.createComponent(MetaCommentsPage);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Pending webhooks');
    expect(fixture.nativeElement.textContent).toContain('Reconcile missed events');
  });
});
