import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, afterEach, describe, expect, it } from 'vitest';
import { CreativeStudioPage } from './creative-studio.page';

describe('Step 2 assessment transport and saved-session restoration', () => {
  const key='pompom.creative-studio.v1';
  const alternatives=[
    {candidateId:'candidate-1',title:'Avalanche',text:'Mimi sees notes multiply.'},
    {candidateId:'candidate-2',title:'Shadow',text:'Mimi stops and the note stops.'},
    {candidateId:'candidate-3',title:'Rebellion',text:'Mimi runs and the notes follow.'}
  ];
  const quality={classification:'PARTIALLY_DISTINCT',differences:['Alternative 1 vs 2: different endingEvent'],
    pairs:[{left:1,right:2,differentDimensions:['endingEvent'],sharedDimensions:[]}],
    candidates:alternatives.map((c,i)=>({assessment:{candidateId:c.candidateId,fingerprint:`fp-${i}`,
      strengths:[{message:`Strength ${i+1}`}],risks:i===1?[]:[{message:`Risk ${i+1}`}],unknown:[{message:`Unknown ${i+1}`}]}}))};
  const record={recordId:'story-record',role:'STORY',result:{alternatives,storyQuality:quality}};
  const state={sessionId:'session',storyRecordId:record.recordId,stage:'STORY',activeJourney:'SAVED',
    candidates:alternatives,storyQuality:{classification:'INSUFFICIENT_EVIDENCE',pairs:[],differences:[]},
    selectedCandidateIdValue:'candidate-2',selectedStory:alternatives[1].text,approvalRecordId:'',storyReview:null};
  let http:HttpTestingController;
  beforeEach(async()=>{
    localStorage.clear();
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    http=TestBed.inject(HttpTestingController);
  });
  afterEach(()=>{http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify();localStorage.clear();TestBed.resetTestingModule();});
  function open(saved=false,serverFirst=false){
    if(saved)localStorage.setItem(key,JSON.stringify(state));
    const fixture=TestBed.createComponent(CreativeStudioPage);
    fixture.detectChanges();
    const reads=http.match(r=>r.method==='GET');
    const flush=(r:any)=>r.flush(r.request.url.includes('kind=CREATIVE_ROLE')?[record]:
      r.request.url.includes('/studio-sessions/session')?state:[]);
    reads.filter(r=>!r.request.url.includes('kind=CREATIVE_ROLE')&&!r.request.url.includes('/studio-sessions/session')).forEach(flush);
    const roles=reads.find(r=>r.request.url.includes('kind=CREATIVE_ROLE'));
    const session=reads.find(r=>r.request.url.includes('/studio-sessions/session'));
    if(serverFirst&&session)flush(session);
    if(roles)flush(roles);
    if(!serverFirst&&session)flush(session);
    fixture.detectChanges();
    return {fixture,page:fixture.componentInstance as any};
  }
  function checkCards(fixture:any,page:any){
    expect(page.candidates.map((c:any)=>c.assessment.candidateId)).toEqual(alternatives.map(c=>c.candidateId));
    const cards=fixture.nativeElement.querySelectorAll('.story-card');
    expect(cards).toHaveLength(3);
    Array.from(cards).forEach((card:any,i)=>{
      expect(card.textContent).toContain('PRELIMINARY');
      expect(card.textContent).toContain(`Strength ${i+1}`);
      expect(card.textContent).toContain(`Unknown ${i+1}`);
      expect(card.querySelector('.assessment-risks')!==null).toBe(i!==1);
    });
  }
  it('maps real object alternatives from a fresh response into rendered cards',()=>{
    const {fixture,page}=open();page.idea='Mimi';page.candidateCount=3;
    page.runStoryRole();http.expectOne(r=>r.method==='POST'&&r.url.endsWith('/creative-role')).flush(record);
    http.expectOne(r=>r.method==='PUT').flush({});fixture.detectChanges();checkCards(fixture,page);
  });
  it('maps saved object alternatives into rendered cards',()=>{
    const {fixture,page}=open();page.useSavedStory(page.savedStories[0]);fixture.detectChanges();checkCards(fixture,page);
  });
  for(const serverFirst of [true,false])it(`hydrates stale reload state with server response ${serverFirst?'before':'after'} records`,()=>{
    const {fixture,page}=open(true,serverFirst);checkCards(fixture,page);
    expect(page.selectedCandidateId).toBe('candidate-2');expect(page.approvalRecordId).toBe('');
    expect(page.storyQuality.pairs[0].differentDimensions).toEqual(['endingEvent']);
    const stored=JSON.parse(localStorage.getItem(key)!);
    expect(stored.candidates[1].assessment.fingerprint).toBe('fp-1');
    expect(stored.storyQuality.candidates[1].assessment.fingerprint).toBe('fp-1');
    page.selectStory(page.candidates[2]);http.expectOne(r=>r.method==='PUT').flush({});
    expect(page.approvalRecordId).toBe('');expect(page.stage).toBe('STORY');
  });
  it('does not attach saved assessment to edited text or a reordered candidate set',()=>{
    const {page}=open();page.storyRecordId=record.recordId;page.candidates=alternatives.map(c=>({...c}));
    page.candidates[0].text='A different revision';page.storyQuality=null;page.hydrateSavedStoryAssessment();
    expect(page.storyQuality).toBeNull();expect(page.candidates.every((c:any)=>!c.assessment)).toBe(true);
    page.candidates=[...alternatives].reverse();page.hydrateSavedStoryAssessment();
    expect(page.storyQuality).toBeNull();expect(page.candidates.every((c:any)=>!c.assessment)).toBe(true);
  });
  it('does not invent assessment for an old saved schema',()=>{
    const {page}=open();page.useSavedStory({...page.savedStories[0],result:{alternatives,storyQuality:{classification:'INSUFFICIENT_EVIDENCE'}}});
    expect(page.candidates.every((c:any)=>!c.assessment)).toBe(true);
  });
});
