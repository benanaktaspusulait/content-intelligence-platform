import { TestBed } from '@angular/core/testing';
import { StoryPremiseReportComponent } from './story-premise-report.component';

describe('saved story premise report', () => {
  it('shows revision reasons and short/long suitability without mutating evidence', async () => {
    await TestBed.configureTestingModule({ imports: [StoryPremiseReportComponent] }).compileComponents();
    const fixture = TestBed.createComponent(StoryPremiseReportComponent);
    const input = {
      status: 'STORY_REVISION_REQUIRED', score: 12, archetype: 'PASSIVE_MISUNDERSTANDING',
      humanReadableReport: 'The protagonist never sacrifices an original goal.',
      findings: [{ severity: 'STORY_REVISION_REQUIRED', message: 'No meaningful cost.' }],
      durationSuitability: { '10_20_SECONDS': { status: 'SUITABLE', reason: 'One reveal.' }, '45_75_SECONDS': { status: 'REVISION_REQUIRED', reason: 'Needs an active arc.' } },
      storyEngineSummary: { moralChoice: null },
      checks: [{ checkId: 'MORAL_CHOICE_GATE', outcome: 'UNKNOWN', reason: 'No deliberate choice.', evidence: [{ quote: 'Arda looks scary.' }] }],
      evidenceLimitations: ['Textual support only.'],
    };
    const original = JSON.stringify(input);
    fixture.componentRef.setInput('premise', input); fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('STORY_REVISION_REQUIRED');
    expect(text).toContain('No meaningful cost.');
    expect(text).toContain('10_20_SECONDS'); expect(text).toContain('45_75_SECONDS');
    expect(text).toContain('Arda looks scary.'); expect(text).toContain('separate from canonical scoring');
    expect(JSON.stringify(input)).toBe(original);
    fixture.destroy(); TestBed.resetTestingModule();
  });

  it('adds no section to historical short-form reports', async () => {
    await TestBed.configureTestingModule({ imports: [StoryPremiseReportComponent] }).compileComponents();
    const fixture = TestBed.createComponent(StoryPremiseReportComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('section')).toBeNull();
    fixture.destroy(); TestBed.resetTestingModule();
  });
});
