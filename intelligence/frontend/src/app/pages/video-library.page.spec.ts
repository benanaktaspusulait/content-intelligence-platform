import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { CreativeIntelligenceService, MediaDirectory, MediaFile } from '../core/creative-intelligence.service';
import { MediaFileView, VideoLibraryPage, filterMediaDirectories, groupMediaFilesByFolder, mediaVariant, mergeMediaFiles, resultCountLabel } from './video-library.page';

const folders: MediaDirectory[] = [
  { name: 'Sea Stories', relativePath: 'library/Sea Stories', videoCount: 2 },
  { name: 'Stone Music', relativePath: 'library/Stone Music', videoCount: 2 },
  { name: 'Garden Games', relativePath: 'library/Garden Games', videoCount: 1 },
];

const shared: MediaFile = { name: 'shared.mp4', relativePath: 'library/shared.mp4', sizeBytes: 100, modifiedAt: null, ingested: false, videoId: null, status: null, variantId: null };
const seaFile: MediaFile = { ...shared, name: 'sea.mp4', relativePath: 'library/Sea Stories/sea.mp4' };
const stoneFile: MediaFile = { ...shared, name: 'stone.mp4', relativePath: 'library/Stone Music/stone.mp4' };

describe('VideoLibraryPage folder selection', () => {
  const service = {
    getMediaDirectories: () => of(folders),
    getMediaFiles: (path: string) => of(path.includes('Sea') ? [seaFile, shared] : [stoneFile, shared]),
    ingestDirectory: () => of({ relativeDirectory: '', discovered: 0, ingested: [], errors: [] }),
    ingestVideo: () => of({}),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VideoLibraryPage],
      providers: [provideRouter([]), { provide: CreativeIntelligenceService, useValue: service }],
    }).compileComponents();
  });

  it('filters folder choices immediately and case-insensitively', () => {
    expect(filterMediaDirectories(folders, 'SEA').map(folder => folder.name)).toEqual(['Sea Stories']);

    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();
    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.value = 'STONE';
    search.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const choices = fixture.nativeElement.querySelectorAll('.folder-option');
    expect(choices.length).toBe(1);
    expect(choices[0].textContent).toContain('Stone Music');
  });

  it('closes a populated folder search on the first Escape press', () => {
    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();

    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.dispatchEvent(new Event('focus'));
    search.value = 'sea';
    search.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(search.getAttribute('aria-expanded')).toBe('true');

    const escape = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true });
    search.dispatchEvent(escape);
    fixture.detectChanges();

    expect(escape.defaultPrevented).toBe(true);
    expect(search.value).toBe('sea');
    expect(search.getAttribute('aria-expanded')).toBe('false');
    expect(fixture.nativeElement.querySelector('.folder-menu')).toBeNull();
  });

  it('supports multi-selection and renders a deduplicated combined file list', () => {
    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();

    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.dispatchEvent(new Event('focus'));
    fixture.detectChanges();

    const choices = fixture.nativeElement.querySelectorAll('.folder-option input') as NodeListOf<HTMLInputElement>;
    choices[0].click();
    choices[1].click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('.folder-chips > span').length).toBe(2);
    expect(fixture.nativeElement.querySelectorAll('.media-files-table tbody tr').length).toBe(3);
    expect(fixture.nativeElement.querySelectorAll('.media-file-group').length).toBe(3);
    expect(fixture.nativeElement.textContent).toContain('3 groups · 3 files');
  });
});

describe('variant identity grouping', () => {
  const service = {
    getMediaDirectories: () => of(folders),
    getMediaFiles: () =>
      of([
        { ...shared, name: 'take1.mp4', relativePath: 'library/Sea Stories/take1.mp4', variantId: 'variant-1' },
        { ...shared, name: 'weird_name_hd.mp4', relativePath: 'library/Sea Stories/weird_name_hd.mp4', variantId: 'variant-1' },
      ]),
    ingestDirectory: () => of({ relativeDirectory: '', discovered: 0, ingested: [], errors: [] }),
    ingestVideo: () => of({}),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VideoLibraryPage],
      providers: [provideRouter([]), { provide: CreativeIntelligenceService, useValue: service }],
    }).compileComponents();
  });

  it('groups two differently-named files under the same real variant into one row group', () => {
    const fixture = TestBed.createComponent(VideoLibraryPage);
    fixture.detectChanges();
    const search = fixture.nativeElement.querySelector('#folder-search') as HTMLInputElement;
    search.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    const choice = fixture.nativeElement.querySelector('.folder-option input') as HTMLInputElement;
    choice.click();
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('.media-files-table tbody tr');
    expect(rows.length).toBe(2);
    const labels = [...rows].map((row: HTMLElement) => row.querySelector('td strong')!.textContent);
    expect(labels).toEqual(['Original 1', 'HD 2']);
  });
});

describe('mergeMediaFiles', () => {
  it('deduplicates by relative path', () => {
    expect(mergeMediaFiles([[seaFile, shared], [stoneFile, shared]])).toHaveLength(3);
  });
});

describe('groupMediaFilesByFolder', () => {
  const view = (file: MediaFile, folderPath: string, variantName: string): MediaFileView => ({
    ...file,
    displayName: `${folderPath} · ${variantName}`,
    folderName: folderPath.split('/').pop()!,
    folderPath,
    variantName,
  });

  it('keeps variants from the same physical folder in one group', () => {
    const original = view(seaFile, 'library/Sea Stories/01_seed', 'Original');
    const hd = view({ ...seaFile, name: 'sea_hd.mp4', relativePath: 'library/Sea Stories/01_seed/sea_hd.mp4' }, 'library/Sea Stories/01_seed', 'HD');

    const groups = groupMediaFilesByFolder([original, hd]);

    expect(groups).toHaveLength(1);
    expect(groups[0].files.map(file => file.variantName)).toEqual(['Original', 'HD']);
  });

  it('keeps files from different physical folders in separate groups', () => {
    const groups = groupMediaFilesByFolder([
      view(seaFile, 'library/Sea Stories/01_seed', 'Original'),
      view(stoneFile, 'library/Stone Music/02_stone', 'Original'),
    ]);

    expect(groups.map(group => group.folderPath)).toEqual(['library/Sea Stories/01_seed', 'library/Stone Music/02_stone']);
  });
});

describe('mediaVariant', () => {
  it('recognizes vertical HD export suffixes', () => {
    expect(mediaVariant('16_arda_sock_big_small_HD_1080x1920.mp4')).toBe('HD');
  });
});

describe('resultCountLabel', () => {
  it('pluralizes group and file counts independently', () => {
    expect(resultCountLabel(1, 1)).toBe('1 group · 1 file');
    expect(resultCountLabel(1, 2)).toBe('1 group · 2 files');
    expect(resultCountLabel(2, 1)).toBe('2 groups · 1 file');
    expect(resultCountLabel(2, 2)).toBe('2 groups · 2 files');
  });
});
