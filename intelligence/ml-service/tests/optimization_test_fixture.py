import json
from copy import deepcopy
from pathlib import Path

def valid_optimization_fixture():
    request=json.loads((Path(__file__).parent/'fixtures/optimization-failed-request.json').read_text())
    source=request['text'];context=deepcopy(request['context'])
    prefix=source.replace('Content profile: AUTO','Content profile: ABSURD_PHYSICS')
    a=prefix.replace('[close-up on', '[extreme close-up on',1)
    b=prefix.replace('2-5s:','2-6s:').replace('5-10s:','6-10s:')
    return source,context,[dict(candidateId='candidate-a',title='Opening clarity',hypothesis='Extreme close framing makes the existing contact anomaly legible.',prompt=a),dict(candidateId='candidate-b',title='Progression pacing',hypothesis='Allocate one more second to separation and shorten the multiplication interval.',prompt=b)]
