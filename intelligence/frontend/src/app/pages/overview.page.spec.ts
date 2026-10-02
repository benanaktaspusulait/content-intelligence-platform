import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { CreativeIntelligenceService } from '../core/creative-intelligence.service';
import { OverviewPage } from './overview.page';

describe('OverviewPage', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OverviewPage],
      providers: [
        provideRouter([]),
        { provide: CreativeIntelligenceService, useValue: { getOverview: () => of({ source: 'api', videos: [], predictions: [] }) } },
      ],
    }).compileComponents();
  });

  it('renders persisted counts without demo data', () => {
    const fixture = TestBed.createComponent(OverviewPage);
    fixture.detectChanges();
    const content = fixture.nativeElement.textContent;
    expect(content).toContain('No videos ingested');
    expect(content).toContain('No predictions recorded');
    expect(content).not.toContain('DEMO DATA');
  });
});
