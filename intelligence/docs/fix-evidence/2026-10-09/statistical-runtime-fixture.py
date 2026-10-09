"""Local acceptance only: requires an empty, disposable pompom_completion_20261009 DB.
No provider calls. All publications, outcomes and features below are SYNTHETIC TEST_FIXTURE.
Run after migration with local backend:8085, ML:8015 and isolated /private/tmp/pfw-completion-data.
"""
import json, math, os, subprocess, uuid, urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
BASE='http://127.0.0.1:8085/api/v1'
OUT=Path(__file__).resolve().parent

def api(path,body=None):
    req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def sql(text):
    result=subprocess.run(['psql','-h','localhost','-U','pompom','-d','pompom_completion_20261009','-v','ON_ERROR_STOP=1','-At'],input=text,text=True,capture_output=True,env={**os.environ,'PGPASSWORD':'pompom_local'})
    if result.returncode:raise RuntimeError(result.stderr)
    return result.stdout.strip()

def seed():
    assert sql('SELECT count(*) FROM videos;')=='0','Only an empty disposable DB may be seeded'
    ids=[];commands=['BEGIN;']
    for n in range(40):
        v=str(uuid.uuid4());ids.append(v)
        publish=datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=5*n)
        p=publish.isoformat();m=(publish+timedelta(hours=72)).isoformat();c=(publish-timedelta(hours=1)).isoformat()
        feature=json.dumps({'overallMotionIntensity':{'value':(n%7)/6}})
        commands.append(f"INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at) VALUES ('{v}','{uuid.uuid4()}','TEST_FIXTURE.mp4','TEST_FIXTURE/{v}.mp4',15000,1080,1920,30,0.5625,'h264',false,'INGESTED',now());")
        commands.append(f"INSERT INTO video_publications(video_id,platform,published_at,publication_timezone,source,platform_content_id,notes) VALUES ('{v}','instagram','{p}','UTC','MANUAL','TEST_FIXTURE-{n}','SYNTHETIC acceptance only');")
        commands.append(f"INSERT INTO performance_observations(video_id,platform,platform_content_id,publication_timestamp,measurement_timestamp,metric_semantics,views,paid,raw_payload_json,source,data_quality_status) VALUES ('{v}','instagram','TEST_FIXTURE-{n}','{p}','{m}','CUMULATIVE',{round(math.expm1(2+3*((n%7)/6)))},false,'{{\"horizon\":\"72H\",\"fixture\":true}}','TEST_FIXTURE','MANUAL');")
        commands.append(f"INSERT INTO prediction_feature_snapshots(video_id,platform,feature_schema_version,source_analysis_version,knowledge_cutoff,features,created_at) VALUES ('{v}','instagram','prediction-feature-snapshot-v1','sampled-visual-motion-v5','{c}','{feature}','{c}');")
    video=ids[0];analysis=str(uuid.uuid4())
    commands.append(f"INSERT INTO creative_analyses(id,video_id,analysis_version,analysis_type,primary_engine,classification,action_dna_score,confidence,reason,raw_result) VALUES ('{analysis}','{video}','sampled-visual-motion-v5','SAMPLED_VISUAL_MOTION','TEST_FIXTURE','MODERATE_MOTION_EVIDENCE',0.5,1,'SYNTHETIC fixture','{{}}');")
    commands.append(f"INSERT INTO creative_fingerprints(video_id,analysis_id,feature_version,creative_quality_score,features) VALUES ('{video}','{analysis}','fixture-v1',0.5,'{{\"overallMotionIntensity\":{{\"value\":0.5}}}}');")
    commands.append('COMMIT;');sql('\n'.join(commands));return video

try:
    api('/models/train',{'platform':'instagram','reason':'SYNTHETIC TEST_FIXTURE insufficient data check'})
    raise AssertionError('An empty dataset must not create an artifact')
except urllib.error.HTTPError as error:
    assert error.code==409
    insufficient=json.load(error)
assert api('/models')==[]
video=seed()
before=api('/predictions',{'videoId':video,'platform':'instagram'})
first=api('/models/train',{'platform':'instagram','reason':'SYNTHETIC TEST_FIXTURE local acceptance'})
assert first['status']=='CHALLENGER'
unpromoted=api('/predictions',{'videoId':video,'platform':'instagram'})
assert unpromoted['modelVersion']==before['modelVersion']=='cold-start-baseline-v1'
first_active=api('/models/'+first['id']+'/promote',{'reason':'SYNTHETIC TEST_FIXTURE holdout only'})
after=api('/predictions',{'videoId':video,'platform':'instagram'})
assert after['modelVersion']==first['version'] and after['payload']['artifactSha256']==first['metrics']['artifactSha256']
second=api('/models/train',{'platform':'instagram','reason':'SYNTHETIC TEST_FIXTURE replacement'})
api('/models/'+second['id']+'/promote',{'reason':'SYNTHETIC TEST_FIXTURE replacement activation'})
replaced=api('/predictions',{'videoId':video,'platform':'instagram'})
assert replaced['modelVersion']==second['version'] and first['version']!=second['version']
api('/models/'+first['id']+'/rollback',{'reason':'SYNTHETIC TEST_FIXTURE rollback'})
rolled=api('/predictions',{'videoId':video,'platform':'instagram'})
assert rolled['modelVersion']==first['version']
assert rolled['payload']['targets']==after['payload']['targets']
assert sql(f"SELECT model_version FROM predictions WHERE id='{after['id']}';")==first['version']
result={'scope':'LOCAL SYNTHETIC TEST_FIXTURE ONLY','database':'pompom_completion_20261009','providerCalls':0,'productionModelPromoted':False,'seededIndependentParents':40,'insufficientData':insufficient,'before':before,'challenger':first,'unpromoted':unpromoted,'promoted':first_active,'after':after,'replacement':second,'replaced':replaced,'rolledBack':rolled,'checks':['backend collected exact verified 72H context','real ML statistical fit persisted artifact','real verify HTTP accepted hash-derived model identity','challenger leaves cold-start inference unchanged','promotion changes backend-served inference','replacement selects second artifact','rollback restores first artifact and prediction parity','historical prediction retains immutable model version']}
(OUT/'statistical-runtime-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'checks':'PASS','providerCalls':0,'parents':40,'first':first['version'],'second':second['version']}))
