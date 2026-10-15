#!/usr/bin/env python3
"""Deterministic saved-source engineering cohort; never a provider call."""
import json
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'intelligence/ml-service'),str(ROOT/'intelligence/ml-service/tests')]
from test_creative_reconstruction_v2 import fixture,plan,response,MockProvider,canonical_review
from app.workflow.creative_roles import perform_role
from app.workflow.optimization_comparison import assess_comparison
out=ROOT/'output/verification/creative-optimization-v2'
f=fixture()
cosmetic=plan();cosmetic['interventions'][0]['operation']='CAMERA_LABEL'
timing=plan();timing['interventions'][0]['operation']='TIMING_SPLIT'
story=plan();story['storyChangeRequested']=True
cases={'material_spatial_reconstruction':response(), 'camera_wording_only':response([cosmetic]),
       'unchanged_action_timestamp_split':response([timing]),'execution_risk_regression':response([plan(camera='TRACK')]),
       'protected_story_change':response([story]),'keep_original':{'proposals':[],'noImprovementReason':'No source-supported improvement hypothesis can be justified for this case.'}}
reports=[]
with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No real providers')):
 for name,raw in cases.items():
  result=perform_role('PROMPT_OPTIMIZATION',f['text'],f['context'],MockProvider(raw),'offline-mock-only')
  for c in result['result']['candidates']:c['review']=canonical_review(f,c)
  assessed=assess_comparison(f['text'],result['result']['candidates'],f['context'],f['baselineScore'])
  reports.append({'case':name,'generated':result['result'],'assessment':assessed,'realProviderCalls':0,'promptVersionsCreated':0})
(out/'offline-cohort.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
for r in reports:print(r['case'],r['assessment']['recommendation'],[c['classification'] for c in r['assessment']['candidates']], [c['classification'] for c in r['generated']['rejectedProposals']])
