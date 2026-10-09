"""Contract test with real local video metadata, and explicitly SIMULATED operator observations.
No claim of human or VLM inspection. No provider calls. Isolated disposable DB only.
"""
import json,urllib.request
from pathlib import Path
BASE='http://127.0.0.1:8085/api/v1'
OUT=Path(__file__).resolve().parent

def api(path,body=None):
    req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
video=api('/videos/ingest',{'relativePath':'library/fix-fixtures/AUDIT_FIXTURE_EDITED.mp4'})
video_id=video['id']
values={'coreEventReadability':'ADEQUATE','identity':'RECOGNIZABLE','safety':'APPROPRIATE','coherence':'ADEQUATE','progression':'DEVELOPING','opening':'READABLE_PROMISE','ending':'DELIVERS_PROMISE'}

def body(reviewed,reference):
    experience={key:{'value':value,'start':0,'end':video['durationMs']/1000,'observed':'LOCAL_MOCK simulated operator evidence; not an actual human assessment','confidence':'HIGH','evidenceBasis':'HUMAN_REVIEWED_CLIP','reference':reference} for key,value in values.items()}
    return {'humanReviewed':reviewed,'observation':{'coverage':[0,video['durationMs']/1000],'experience':experience}}
path='/intelligence/workflow/videos/'+video_id+'/qa'
unreviewed=api(path,body(False,video_id))
assert unreviewed['viewerFacingUsability']=='UNKNOWN' and unreviewed['planFidelity']=='NOT_EVALUATED'
simulated=api(path,body(True,video_id))
assert simulated['viewerFacingUsability']=='USABLE' and simulated['planFidelity']=='NOT_EVALUATED'
wrong=api(path,body(True,'00000000-0000-0000-0000-000000000000'))
assert wrong['viewerFacingUsability']=='UNKNOWN'
reopened=api(path)
assert reopened[0]['recordId']==wrong['recordId']
assert all(row['planFidelity']=='NOT_EVALUATED' for row in reopened)
result={'scope':'LOCAL_MOCK operator observations + real local metadata/HTTP/persistence; no human/VLM judgement claim','providerCalls':0,'videoId':video_id,'video':video,'unreviewed':unreviewed,'simulatedOperator':simulated,'wrongReference':wrong,'reopenedRecordIds':[r['recordId'] for r in reopened],'checks':['unreviewed claims remain UNKNOWN','exact UI video UUID resolves to server interval reference','simulated grounded input reaches real ML decision','different video reference remains UNKNOWN','original plan fidelity never inferred','latest persisted record reopens without paid call']}
(OUT/'actual-only-runtime-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'checks':'PASS','providerCalls':0,'videoId':video_id,'latestRecordId':wrong['recordId']}))
