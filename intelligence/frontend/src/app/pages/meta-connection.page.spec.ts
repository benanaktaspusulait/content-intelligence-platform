import { of } from 'rxjs';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MetaReadService } from '../core/meta-read.service';
import { MetaConnection } from '../core/meta-read.models';
import { MetaConnectionPage } from './meta-connection.page';

describe('MetaConnectionPage', () => {
  const connection: MetaConnection = {
    status: 'CONNECTED',
    connected: true,
    readOnlyAnalytics: true,
    page: { id: '123456', name: 'Pompom Hills', category: 'Education' },
    instagramAccount: null,
    lastValidatedAt: '2026-10-01T12:00:00Z',
    apiVersion: 'v26.0',
    requiredPermissions: [],
    optionalPermissions: [
      { permission: 'pages_show_list', status: 'AVAILABLE', message: 'Verified.' },
    ],
    pageManagementVerification: 'VERIFIED',
    message: 'Meta read-only analytics connection is available.',
  };

  it('shows only the configured Page and its management verification result', async () => {
    await TestBed.configureTestingModule({
      imports: [MetaConnectionPage],
      providers: [
        provideRouter([]),
        {
          provide: MetaReadService,
          useValue: {
            getConnection: () => of(connection),
            getPageContent: () =>
              of({
                availability: 'AVAILABLE',
                unavailableReason: null,
                page: connection.page,
                posts: [],
                apiVersion: 'v26.0',
              }),
          },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(MetaConnectionPage);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Facebook Page');
    expect(text).toContain('Pompom Hills');
    expect(text).toContain('Management verification:');
    expect(text).toContain('VERIFIED');
    expect(text).not.toContain('Other Managed Page');
  });
});
