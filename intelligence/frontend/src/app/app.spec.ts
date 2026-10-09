import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [App], providers: [provideRouter([])] }).compileComponents();
  });

  it('creates the application shell', () => {
    expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
  });

  it('renders the full operational navigation', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const links = fixture.nativeElement.querySelectorAll('.primary-nav a');
    expect(links.length).toBe(16);
    expect(fixture.nativeElement.textContent).toContain('Meta Analytics');
    expect(fixture.nativeElement.textContent).toContain('Operations');
    expect(fixture.nativeElement.textContent).toContain('Creative Intelligence');
  });

  it('collapses the desktop navigation rail to free workspace width', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const toggle = fixture.nativeElement.querySelector('.sidebar-toggle') as HTMLButtonElement;
    toggle.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.app-frame--nav-collapsed')).toBeTruthy();
    expect(toggle.getAttribute('aria-label')).toBe('Expand navigation');
  });
});
