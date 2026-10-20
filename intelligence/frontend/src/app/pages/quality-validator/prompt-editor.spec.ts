import { TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';
import { QualityValidatorComponent } from './quality-validator.component';
import { PostFamilyWorkflowComponent } from './post-family-workflow.component';

const monaco = vi.hoisted(() => ({ create: vi.fn(), defineTheme: vi.fn(), editors: [] as any[] }));
vi.mock('monaco-editor/esm/vs/editor/editor.api', () => ({ editor: monaco }));

// Test the real conditional template and async hydration; real Monaco is tested in-browser.
describe('Step 3 prompt editor and immutable revision save', () => {
  let http: HttpTestingController;
  const saved = 'Saved prompt with exact whitespace.\n\n' + 'Original instructions. '.repeat(8);
  beforeEach(async () => {
    monaco.editors = [];
    monaco.create.mockReset();
    monaco.create.mockImplementation((host: HTMLElement, options: any) => {
      const input = document.createElement('textarea');
      input.value = options.value; input.readOnly = options.readOnly; host.append(input);
      let changed = () => {};
      const model = { dispose: vi.fn() };
      const editor = {
        input, model, getValue: () => input.value,
        setValue: (value: string) => { input.value = value; changed(); },
        getModel: () => model, layout: vi.fn(),
        onDidChangeModelContent: (listener: () => void) => { changed = listener; return { dispose: vi.fn() }; },
        dispose: vi.fn(() => input.remove()),
      };
      input.addEventListener('input', () => changed()); monaco.editors.push(editor); return editor;
    });
    await TestBed.configureTestingModule({
      imports: [QualityValidatorComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), {
        provide: ActivatedRoute, useValue: { snapshot: { url: [{ path: 'detail' }], queryParamMap: convertToParamMap({ studio: '1', stage: '3', contentId: '13', promptVersionId: '18' }) } },
      }],
    }).overrideComponent(QualityValidatorComponent, {
      remove: { imports: [PostFamilyWorkflowComponent] }, add: { schemas: [NO_ERRORS_SCHEMA] },
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { try { http.verify(); } finally { TestBed.resetTestingModule(); } });
  function flushSaved() {
    http.expectOne(r => r.url.startsWith('/api/v1/videos/prompt-workspaces?')).flush([]);
    http.expectOne('/api/v1/intelligence/contents/quality-summary').flush([]);
    http.expectOne('/api/v1/intelligence/contents/13/prompt-versions').flush([{ id: 18, versionNumber: 2, rawText: saved }]);
    http.expectOne('/api/v1/intelligence/contents/13/prompt-versions/18/creative-provenance').flush({ origin: 'MANUAL_OR_LEGACY' });
    http.expectOne('/api/v1/intelligence/contents/13/prompt-versions/18/videos').flush([]);
    http.expectOne('/api/v1/intelligence/contents/13').flush({ title: 'Kiko and the Teddy Bear Rejecting Box', type: 'SHORT' });
    // Retrieves stored analysis only; no new analysis.
    http.expectOne('/api/v1/intelligence/quality/validations/latest').flush(null);
  }
  it('opens stage=3 and hydrates saved text arriving after editor creation', async () => {
    const fixture = TestBed.createComponent(QualityValidatorComponent);
    fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); await vi.dynamicImportSettled(); await fixture.whenStable();
    expect(fixture.componentInstance.studioStage).toBe(3);
    expect(monaco.create).toHaveBeenCalledTimes(1);
    flushSaved(); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(monaco.editors[0].input.value).toBe(saved);
    expect(monaco.editors[0].input.readOnly).toBe(false);
    expect(fixture.nativeElement.querySelector('.char-count').textContent).toContain(`${saved.length} characters`);
    http.expectNone(r => r.method === 'POST'); fixture.destroy();
    expect(monaco.editors[0].model.dispose).toHaveBeenCalledOnce();
  });
  it('initializes on later entry and retains unsaved edits after leaving and returning', async () => {
    const fixture = TestBed.createComponent(QualityValidatorComponent); const page = fixture.componentInstance;
    page.studioStage = 4; fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); flushSaved();
    expect(monaco.create).not.toHaveBeenCalled();
    page.scrollToQualityStep('prompt-editor'); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); await vi.dynamicImportSettled(); await fixture.whenStable();
    const first = monaco.editors[0]; expect(first.input.value).toBe(saved);
    first.input.value = saved + ' Edited.'; first.input.dispatchEvent(new Event('input'));
    page.studioStage = 4; fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    expect(first.dispose).toHaveBeenCalledOnce(); expect(first.model.dispose).toHaveBeenCalledOnce();
    page.scrollToQualityStep('prompt-editor'); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); await vi.dynamicImportSettled(); await fixture.whenStable();
    expect(monaco.create).toHaveBeenCalledTimes(2);
    expect(monaco.editors[1].input.value).toBe(saved + ' Edited.'); fixture.destroy();
  });
  it('saves user input as a child revision with a matching count and no analysis dispatch', async () => {
    const fixture = TestBed.createComponent(QualityValidatorComponent);
    fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); flushSaved(); await vi.dynamicImportSettled(); await fixture.whenStable();
    const input = monaco.editors[0].input;
    const edited = saved.replace('Original instructions.', 'Clear original instructions.');
    input.value = edited; input.dispatchEvent(new Event('input')); await vi.dynamicImportSettled(); await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('.char-count').textContent).toContain(`${edited.length} characters`);
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const button = [...fixture.nativeElement.querySelectorAll('button')].find((b: any) => b.textContent.trim() === 'Save revision') as HTMLButtonElement;
    button.click();
    const request = http.expectOne('/api/v1/intelligence/contents/13/prompt-versions');
    expect(request.request.method).toBe('POST'); expect(request.request.body.rawText).toBe(edited);
    expect(request.request.body.parentPromptVersionId).toBe(18); request.flush({ id: 99 });
    expect(fixture.componentInstance.promptVersionId).toBe('99');
    expect(navigate).toHaveBeenCalledWith(['/quality/detail'], expect.objectContaining({ queryParams: expect.objectContaining({ promptVersionId: '99' }) }));
    http.expectNone(r => r.method !== 'GET'); fixture.destroy();
  });
  it('ignores a lazy initialization that finishes after its host was removed', async () => {
    const fixture = TestBed.createComponent(QualityValidatorComponent); fixture.changeDetectorRef.markForCheck(); fixture.detectChanges();
    fixture.componentInstance.studioStage = 4; fixture.changeDetectorRef.markForCheck(); fixture.detectChanges(); flushSaved(); await vi.dynamicImportSettled(); await fixture.whenStable();
    expect(monaco.create).not.toHaveBeenCalled(); fixture.destroy();
  });
});
