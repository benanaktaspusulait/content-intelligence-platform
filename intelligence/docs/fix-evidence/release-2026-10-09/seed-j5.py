import json,uuid,hashlib,subprocess,shutil,urllib.request
from pathlib import Path
ROOT=Path('/private/tmp/pfw-completion-data'); E=Path('/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/fix-evidence/release-2026-10-09')
def api(path,value=None):
 r=urllib.request.Request('http://localhost:8086/api/v1/intelligence/'+path,data=None if value is None else json.dumps(value).encode(),headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(r))
def sql(query):
 p=subprocess.run(['docker','exec','-i','intelligence-postgres-1','psql','-U','pompom','-d','pompom_release_20261009','-At','-v','ON_ERROR_STOP=1'],input=query,text=True,capture_output=True);assert p.returncode==0,p.stderr;return p.stdout.strip().splitlines()[0]
def q(s):return "'"+str(s).replace("'","''")+"'"
frame='library/fix-fixtures/J5-frame.jpg';shutil.copy(next((ROOT/'semantic-frames').rglob('*.jpg')),ROOT/frame)
video='library/fix-fixtures/AUDIT_FIXTURE_EDITED.mp4';vh=hashlib.sha256((ROOT/video).read_bytes()).hexdigest();fh=hashlib.sha256((ROOT/frame).read_bytes()).hexdigest()
c=api('contents',{'title':'LOCAL_MOCK J5 parent-linked queue acceptance','type':'REEL'})['id']
old=api(f'contents/{c}/prompt-versions',{'rawText':'LOCAL_MOCK_J5 original: Luca pushes a box.','parsedIr':'{}'})['id']
new=api(f'contents/{c}/prompt-versions',{'rawText':'LOCAL_MOCK_J5 revision: Luca pushes a box slowly. The camera holds a clear uninterrupted six second view of Luca and the box.','parsedIr':'{}','parentPromptVersionId':old})['id']
text=api(f'contents/{c}/prompt-versions/{new}')['promptText'];ph=hashlib.sha256(text.encode()).hexdigest()
vid=sql('select id from videos where content_hash='+q(vh)+';') if sql('select count(*) from videos where content_hash='+q(vh)+';')!='0' else str(uuid.uuid4())
sql(f"INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at) VALUES ({q(vid)},{q(vh)},'LOCAL_MOCK_J5.mp4',{q(video)},12083,1080,1920,24,.5625,'h264',false,'READY',now()) ON CONFLICT DO NOTHING;")
run=str(uuid.uuid4());primaryrun=str(uuid.uuid4());aset=str(uuid.uuid4());asset=str(uuid.uuid4());dt='2026-10-09T09:10:00Z';rules='1.7+profile-admission-v1:'+ph
report=json.dumps({'preRenderAssessment':{'canonicalProfileAdmission':{'version':'profile-admission-v1','requiredEvidencePreserved':True}},'fixture':'LOCAL_MOCK synthetic independent and visual grades'})
fields='prompt_text,ruleset_version,status,content_id,prompt_version_id,prompt_sha256,deterministic_ruleset_version,semantic_provider,semantic_model_version,validated_at,expires_at,validation_run_id,report_json'
base=f"{q(text)},'1.7','RENDER_READY',{c},{new},{q(ph)},{q(rules)},'LOCAL_MOCK','fixture-independent-v1',{q(dt)},now()+interval '2 days'"
ind=sql(f'INSERT INTO quality_validations({fields}) VALUES ({base},{q(run)},{q(report)}) RETURNING id;')
validation=sql(f'INSERT INTO quality_validations({fields},independent_revalidation_id,independently_revalidated_at) VALUES ({base},{q(primaryrun)},{q(report)},{q(run)},{q(dt)}) RETURNING id;')
for gate in ['FIRST_FRAME','SILHOUETTE']:
 sql(f"INSERT INTO quality_validation_visual_evidence(validation_record_id,content_id,prompt_version_id,prompt_sha256,visual_gate,status,evidence_set_id,render_asset_id,asset_relative_path,asset_sha256,reason,submission_key,verification_id,verified_at) VALUES ({validation},{c},{new},{q(ph)},{q(gate)},'PASS',{q(aset)},{q(asset)},{q(frame)},{q(fh)},'LOCAL_MOCK synthetic grade; no human/video quality claim',{q(str(uuid.uuid4()))},'LOCAL_MOCK',now());")
sql(f"UPDATE contents SET status='RENDER_READY' WHERE id={c};")
options={'profile':'post-family-v1','contentProfile':'CURIOSITY_ADVENTURE','generator':'SEEDANCE_2_0_MINI','desiredDuration':6,'settings':{'mode':'image2video','aspectRatio':'9:16','resolution':'480p'},'references':[{'kind':'FIRST_FRAME','relativePath':frame}],'canonicalValidationId':int(validation)}
review=api('workflow/review',{'contentId':c,'promptVersionId':new,'options':options})
origin=str(uuid.uuid4());qa=str(uuid.uuid4());orig={'contentId':c,'promptVersionId':old,'bindingHash':'a'*64,'fixture':'LOCAL_MOCK source review'}
payload={'videoId':vid,'relativePath':video,'assetHash':vh,'reviewId':origin,'repairEconomics':{'fullRerenderJustified':True},'fixture':'LOCAL_MOCK synthetic justification'}
for id,kind,data in [(origin,'REVIEW',orig),(qa,'ACTUAL_RENDER_QA',payload)]:sql(f"INSERT INTO post_family_workflow_events(id,kind,payload) VALUES ({q(id)},{q(kind)},{q(json.dumps(data))}::jsonb);")
result={'contentId':c,'originalPromptVersionId':old,'promptVersionId':new,'validationId':int(validation),'reviewId':review['recordId'],'parentVideoId':vid,'qaRecordId':qa,'frame':frame,'frameHash':fh,'parentHash':vh,'fixture':'LOCAL_MOCK grades; real copied bytes/persistence/admission'}
(E/'j5-source.json').write_text(json.dumps(result,indent=2));(E/'j5-review.json').write_text(json.dumps(review,indent=2));print(json.dumps(result));print(review['family8']['renderAuthorization'])
