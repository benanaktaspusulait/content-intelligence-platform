"""Create isolated UI fixtures from an authoritative GET snapshot; no providers."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ml-service'))
from app.workflow.idea_evaluation import payload_hash
from app.workflow.idea_review import DIMENSIONS,VERSION
s=json.load(open(sys.argv[1]))
rows=[]
for i,c in enumerate(s['candidates']):
 p=c['payload']; judgments=[]
 for d,r in DIMENSIONS.items():
  field={'EVERYDAY_GOAL':'everydayGoal','IMMEDIATE_CONFLICT':'frameZeroProblem','TEXTUAL_OPENING_CAUSALITY':'firstStaticFrame','SINGLE_RULE':'impossibleRule','RULE_CONSISTENCY':'discovery','CHARACTER_MOTIVATION':'everydayGoal','CAUSAL_PROGRESSION':'proposedProgression','POTENTIAL_VISUAL_BEATS':'proposedProgression','PAYOFF_SALIENCE':'payoff','REPLAY_POTENTIAL':'viewerQuestion','ORIGINALITY_RISK':'concept','PRODUCTION_FEASIBILITY':'productionRisk'}[d]
  verdict='SEMANTIC_UNKNOWN' if i==1 else 'SEMANTIC_FAIL' if d=='RULE_CONSISTENCY' else 'SEMANTIC_PASS'
  if d in {'ORIGINALITY_RISK','PRODUCTION_FEASIBILITY'}:verdict='VISUAL_EVIDENCE_REQUIRED'
  if d=='POTENTIAL_VISUAL_BEATS':verdict='LATER_STAGE_EVIDENCE'
  judgments.append(dict(dimension=d,ruleId=r,verdict=verdict,evidence=[dict(field=field,quote=p[field])],comparisonEvidence=[],reason='SYNTHETIC ACCEPTANCE FIXTURE ONLY. This varied verdict exercises contract/UI handling; it is not an independent creative judgment about Arda.',confidence=.5))
 rows.append(dict(candidateId=c['candidateId'],sourcePayloadSha256=payload_hash(p),originalEvaluationRevision=c['evaluation']['revision'],judgments=judgments))
Path(__file__).with_name('idea_review.json').write_text(json.dumps(dict(policyVersion=VERSION,reviewerModel='fixture-transport-v1',reviewerVersion='fixture-transport-v1',candidateReviews=rows),ensure_ascii=False,indent=2)+'\n')
