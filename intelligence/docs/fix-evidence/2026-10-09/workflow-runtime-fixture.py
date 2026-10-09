"""Isolated local acceptance. Seeded story/draft/review facts are LOCAL_MOCK, not live model output.
No provider calls. Must use disposable pompom_completion_20261009 backend:8085 and local ML:8015.
"""
import json, os, subprocess, uuid, urllib.request, urllib.parse
from pathlib import Path
BASE='http://127.0.0.1:8085/api/v1/intelligence'
OUT=Path(__file__).resolve().parent

def api(path,body=None):
    req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def seed(kind,payload):
    record=str(uuid.uuid4())
    value=json.dumps(payload).replace("'","''")
    result=subprocess.run(['psql','-h','localhost','-U','pompom','-d','pompom_completion_20261009','-v','ON_ERROR_STOP=1'],input=f"INSERT INTO post_family_workflow_events(id,kind,payload) VALUES ('{record}','{kind}','{value}');",text=True,capture_output=True,env={**os.environ,'PGPASSWORD':'pompom_local'})
    assert result.returncode==0,result.stderr
    return record
readiness=api('/workflow/creative-role/readiness')
assert not readiness['enabled'] and not readiness['liveVerified']
story=seed('CREATIVE_ROLE',{'role':'STORY','provider':'LOCAL_MOCK','model':'fixture-story-model','result':{'alternatives':['LOCAL_MOCK story']}})
draft=seed('CREATIVE_ROLE',{'role':'BUILD_PROMPT','provider':'LOCAL_MOCK','model':'fixture-build-model','sourceStoryRecordId':story,'result':{'prompt':'0-15 SEC\nA pendulum swings. LOCAL_MOCK draft.'}})
content=api('/contents',{'title':'LOCAL_MOCK creative provenance acceptance','type':'REEL'})
saved=api(f"/contents/{content['id']}/prompt-versions",{'rawText':'0-15 SEC\nA pendulum swings. LOCAL_MOCK operator edit.','parsedIr':'{}','creativeRoleRecordId':draft})
provenance=api(f"/contents/{content['id']}/prompt-versions/{saved['id']}/creative-provenance")
assert provenance['creativeRoleRecordId']==draft and provenance['sourceStoryRecordId']==story and provenance['operatorEdited'] and provenance['validationStatus']=='NOT_VALIDATED'
revision=api(f"/contents/{content['id']}/prompt-versions",{'rawText':'0-15 SEC\nA pendulum swings. LOCAL_MOCK later edit.','parsedIr':'{}','parentPromptVersionId':saved['id']})
assert api(f"/contents/{content['id']}/prompt-versions/{revision['id']}/creative-provenance")['creativeRoleRecordId']==draft
cap='openart-cli-schema-2026-10-08';generator='SEEDANCE_2_0_MINI';settings={'mode':'image2video','aspectRatio':'9:16','resolution':'480p'}
source=seed('REVIEW',{'fixture':'LOCAL_MOCK','bindingHash':'b'*64,'contentId':content['id'],'promptVersionId':saved['id'],'routing':{'contentProfile':'EDUCATIONAL'},'generation':{'profileVersion':cap,'selectedGenerator':generator,'settings':settings},'boundRequest':{'desiredDuration':15}})
source_video=str(uuid.uuid4());source_hash='c'*64
sql=f"INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at) VALUES ('{source_video}','{source_hash}','LOCAL_MOCK.mp4','TEST_FIXTURE/{source_video}.mp4',15000,1080,1920,30,0.5625,'h264',false,'INGESTED',now());"
subprocess.run(['psql','-h','localhost','-U','pompom','-d','pompom_completion_20261009','-v','ON_ERROR_STOP=1'],input=sql,text=True,capture_output=True,env={**os.environ,'PGPASSWORD':'pompom_local'},check=True)
qa=seed('ACTUAL_RENDER_QA',{'fixture':'LOCAL_MOCK' ,'lineageStatus':'SOURCE_BOUND','reviewId':source,'videoId':source_video,'assetHash':source_hash,'duration':15,'bindingHash':'b'*64,'viewerFacingUsability':'USABLE'})
lesson=api('/workflow/learning/LESSON',{'hypothesis':'LOCAL_MOCK fixture verifies source-bound retrieval','lessonScope':'ACTUAL_EXECUTION','evidenceBasis':[qa],'sampleSize':1,'targetModelVersion':cap,'settings':settings,'contentProfile':'EDUCATIONAL','durationRange':[15,15],'observedResult':'LOCAL_MOCK only','counterexamples':[]})
params={'contentProfile':'EDUCATIONAL','modelVersion':cap,'duration':15,'generator':generator,'settings':json.dumps(settings)}
query=urllib.parse.urlencode(params)
assert api('/workflow/learning/retrieve?'+query)==[]
approved=api('/workflow/records/'+lesson['recordId']+'/learning-review',{'decision':'APPROVED','reason':'LOCAL_MOCK acceptance only'})
retrieved=api('/workflow/learning/retrieve?'+query)
assert len(retrieved)==1 and retrieved[0]['recordId']==approved['recordId']
options={'profile':'post-family-v1','contentProfile':'EDUCATIONAL','generator':generator,'desiredDuration':15,'lessonModelVersion':cap,'settings':settings}
review=api('/workflow/review',{'contentId':content['id'],'promptVersionId':revision['id'],'options':options})
assert review['retrievedLessons'][0]['recordId']==approved['recordId']
assert review['boundRequest']['retrievedLessons'][0]['recordId']==approved['recordId']
revoked=api('/workflow/records/'+approved['recordId']+'/learning-review',{'decision':'REVOKED','reason':'LOCAL_MOCK revocation acceptance'})
assert api('/workflow/learning/retrieve?'+query)==[]
reopened=api('/workflow/records/'+review['recordId'])
assert reopened['retrievedLessons'][0]['recordId']==approved['recordId'],'Historical review must keep its own immutable lesson snapshot'
refreshed=api('/workflow/review',{'contentId':content['id'],'promptVersionId':revision['id'],'options':options})
assert refreshed['retrievedLessons']==[] and refreshed['bindingHash']!=review['bindingHash']
result={'scope':'LOCAL_MOCK records + real local HTTP/persistence/reopen; no provider execution','providerCalls':0,'readiness':readiness,'storyId':story,'draftId':draft,'contentId':content['id'],'promptVersionId':revision['id'],'provenance':provenance,'approvedLesson':approved,'retrieved':retrieved,'reviewId':review['recordId'],'boundLessonIds':[approved['recordId']],'revoked':revoked,'freshReviewId':refreshed['recordId'],'historicalBinding':review['bindingHash'],'freshBinding':refreshed['bindingHash'],'checks':['edited draft retains story/provider/model metadata','descendant revision inherits source provenance','pending lesson excluded','approved lesson injected into real resolved-capability review','reopened review keeps original lesson snapshot','revocation excludes next request and changes binding']}
(OUT/'workflow-runtime-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'checks':'PASS','providerCalls':0,'contentId':content['id'],'promptVersionId':revision['id']}))
