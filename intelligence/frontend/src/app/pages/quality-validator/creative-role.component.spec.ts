import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { CreativeRoleComponent } from './creative-role.component';

describe('creative role provenance', () => {
  it('renders asynchronous readiness and carries the selected story into a separately requested draft', async () => {
    await TestBed.configureTestingModule({ imports:[CreativeRoleComponent], providers:[provideHttpClient(),provideHttpClientTesting()] }).compileComponents();
    const fixture=TestBed.createComponent(CreativeRoleComponent);
    const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true,liveVerified:false,roles:[]});
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Server execution: enabled');
    const component=fixture.componentInstance;
    component.text='Fixture idea'; component.budget=1;component.consent=true;component.run('STORY');
    const story=http.expectOne('/api/v1/intelligence/workflow/creative-role');
    expect(story.request.body.role).toBe('STORY');
    story.flush({role:'STORY',recordId:'story-fixture',provider:'mock',model:'fixture',result:{alternatives:['Fixture alternative']}});
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('Fixture alternative');
    component.chooseStory('Fixture alternative');component.text+=' edited';component.consent=true;component.run('BUILD_PROMPT');
    const build=http.expectOne('/api/v1/intelligence/workflow/creative-role');
    expect(build.request.body.context.sourceStoryRecordId).toBe('story-fixture');
    expect(build.request.body.text).toBe('Fixture alternative edited');
    build.flush({role:'BUILD_PROMPT',recordId:'draft-fixture',provider:'mock',model:'fixture',result:{prompt:'Fixture draft'}});
    await fixture.whenStable();
    let emitted:any;component.draft.subscribe(value=>emitted=value);
    const button=Array.from(fixture.nativeElement.querySelectorAll('button')).find((b:any)=>b.textContent.includes('Use draft')) as HTMLButtonElement;
    button.click();
    expect(emitted).toEqual({prompt:'Fixture draft',recordId:'draft-fixture'});
    expect(component.consent).toBe(false);
    http.verify();fixture.destroy();TestBed.resetTestingModule();
  });
});
