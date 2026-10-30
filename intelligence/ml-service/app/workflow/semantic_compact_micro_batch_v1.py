"""Fixed three independent requests through the accepted LOW runner; read-only aggregation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean, median

from . import semantic_low_reasoning_probe_v1 as low
from .evidence_supported_admission_v2 import OPENING_FLOOR
from .semantic_live_experiment import write_new

REQUEST_IDS = ('micro-a', 'micro-b', 'micro-c')
EXPERIMENT_ID = 'semantic-compact-micro-batch-v1'


def plan(profile, prior, accepted):
    planned = low.plan(profile, prior)
    if planned['status'] != 'READY' or planned['selectedReasoningEffort'] != 'low':
        raise ValueError('Accepted LOW profile required')
    if planned['newRequest'] != accepted:
        raise ValueError('Request must equal the stored successful LOW request exactly')
    return dict(experimentId=EXPERIMENT_ID, requestIds=list(REQUEST_IDS), maximumLiveRequests=3,
                candidateCountPerRequest=1, request=deepcopy(accepted), retries=0, fallbacks=0,
                DeepSeekCalls=0, renders=0, crossRequestFeedback=False,
                referenceRegenerated=False, promptHash=low.previous.PROMPT_HASH,
                schemaHash=low.previous.SCHEMA_HASH)


def review_reasons(record):
    v = record['validation']; blockers = record['productionBlockers']; out = []
    if record['productionAdmissible']: out.append('PRODUCTION_ADMISSIBLE')
    if v['eligibility'] == 'ELIGIBLE': out.append('RANKING_ELIGIBLE')
    if v['shortFormEngine']['status'] == 'PASS': out.append('SFE_PASS')
    if v['shortFormScore'] >= 75 and len(blockers) == 1: out.append('SFE_GE75_ONE_BLOCKER')
    if record['admission']['admitted'] and len(blockers) == 1: out.append('ADMITTED_ONE_BLOCKER')
    return out


def combine(inspections):
    rows = []
    for identity, inspection in inspections.items():
        if not inspection.get('pipelineRan'): continue
        source = inspection['pipeline']['allRawIdeas'][0]
        r = source['record']
        if not r: continue
        # Provider-local ideaId and accepted pipeline candidateId are preserved verbatim.
        # Globally unique provenance IDs qualify local IDs without changing scoring inputs.
        rows.append(dict(id=identity, candidateId=f'{EXPERIMENT_ID}/{identity}/{r["candidateId"]}',
                         pipelineCandidateId=r['candidateId'], raw=source['raw'], record=r,
                         creativeContract=inspection['creativeContractClassification'],
                         creativeEvidence=inspection['creativeEvidence'],
                         reviewReasons=review_reasons(r)))
    openings = [r['record']['observation']['openingScore'] for r in rows]
    scores = [r['record']['validation']['shortFormScore'] for r in rows]
    above = sum(v >= OPENING_FLOOR for v in openings)
    return dict(sampleSize=len(rows), candidates=rows,
                opening=dict(scores=openings, acceptedFloor=OPENING_FLOOR, atOrAboveFloor=above,
                             belowFloor=len(openings)-above, mean=mean(openings) if openings else None,
                             median=median(openings) if openings else None,
                             signal='NO_CLEAR_PATTERN' if len(rows)<4 else 'OPENING_WEAKNESS_SIGNAL' if above<=1 else 'OPENING_PERFORMANCE_ENCOURAGING' if above>=3 else 'NO_CLEAR_PATTERN',
                             interpretation='Descriptive four-sample observation only; no statistical proof or new admission threshold.'),
                ruleConsistency=dict(Counter(r['creativeEvidence']['ruleConsistency'] for r in rows)),
                payoffRuleLinked=dict(Counter(str(r['record']['observation']['payoffRuleLinked']) for r in rows)),
                admissionStatuses=dict(Counter(r['record']['admission']['status'] for r in rows)),
                BeatGrammar=dict(Counter(r['record']['candidate']['beatGrammar']['beatGrammarQuality'] for r in rows)),
                SFE=dict(scores=scores, mean=mean(scores) if scores else None, median=median(scores) if scores else None,
                         statuses=dict(Counter(r['record']['validation']['shortFormEngine']['status'] for r in rows))),
                rankingEligibleCount=sum(r['record']['validation']['eligibility']=='ELIGIBLE' for r in rows),
                productionAdmissibleCount=sum(r['record']['productionAdmissible'] for r in rows),
                productionSlateMembers=[r['candidateId'] for r in rows if r['record']['productionSlateRank'] is not None],
                MICRO_BATCH_HUMAN_REVIEW_SET=[r['candidateId'] for r in rows if r['reviewReasons']],
                referenceRegenerated=False, providerCallsDuringAnalysis=0, renders=0)


def execute(directory, profile, prior, accepted, reference, *, authorization, tests, executor=None):
    spec = plan(profile, prior, accepted)
    if not tests.get('noNewFailures') or not tests.get('schemaIntegrityPassed') or not authorization:
        raise ValueError('Completed offline tests and authorization required')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)  # Durable whole-batch claim; never resume/retry.
    write_new(directory/'plan.json', spec)
    inspections = {'REFERENCE-0': json.loads(Path(reference).read_text())}
    results = {}
    for identity in REQUEST_IDS:
        path = directory/identity
        write_new(directory/f'{identity}-provenance.json', dict(requestId=identity,
                  globallyUniqueRequestId=f'{EXPERIMENT_ID}/{identity}',
                  referenceSource=str(reference), ordinal=len(results)+1))
        try:
            result = (executor or low.execute)(path, profile, prior, authorization=authorization, tests=tests)
        except Exception as error:
            # A failed planned slot is consumed even if failure precedes transport.
            result = dict(status='FAILED', errorClass=type(error).__name__, replacement=False)
        results[identity] = result
        if (path/'inspection.json').exists():
            inspections[identity] = json.loads((path/'inspection.json').read_text())
        write_new(directory/f'{identity}-result.json', result)
    summary = combine(inspections)
    write_new(directory/'combined-analysis.json', summary)
    write_new(directory/'execution-proof.json', dict(plannedRequests=3, consumedSlots=len(results),
              SDKRequestsForwarded=sum(r.get('SDKRequestsForwarded',0) for r in results.values()),
              HTTPRequestsObserved=sum(r.get('HTTPRequestsObserved',0) for r in results.values()),
              maximumLiveRequests=3, retries=0, replacementRequests=0, fourthRequest=False,
              fallbacks=0, DeepSeekCalls=0, renders=0, referenceRegenerated=False))
    return summary
