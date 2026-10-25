"""Isolated browser acceptance adapter. No external network or provider SDKs.
Run backend against a disposable DB and point ML_SERVICE_URL here, never production.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path('/tmp/pompom-idea-fixture-calls.jsonl')
CANDIDATES = [
    dict(candidateId=f'provider-fixture-{i}', title=title,
         concept=f'Arda tries to {goal} in his lived-in kitchen.',
         everydayGoal=goal, firstStaticFrame=opening, frameZeroProblem=opening,
         impossibleRule=rule, proposedProgression=progression, discovery=progression,
         viewerQuestion='How can Arda finish his ordinary task under this rule?',
         payoff=payoff, productionRisk='Unverified contact and object continuity; no visual proof.')
    for i, (title, goal, opening, rule, progression, payoff) in enumerate([
        ('Fixture: Folded Sunlight', 'fold a tablecloth', 'The cloth corner holds a rigid patch of sunlight while Arda grips it.',
         'Only this cloth folds its cast sunlight into solid layers.',
         'A fold stacks light; the stack changes the cloth balance; unfolding creates a new table shape.',
         'The cloth unfolds into a luminous table-shaped pocket.'),
        ('Fixture: Backward Bowl', 'put a bowl away', 'The bowl hovers against the shelf underside in front of Arda.',
         'This bowl rests only on the underside of horizontal surfaces.',
         'An underside rest shifts the reach; a rotated tray changes the carrying strategy; the final underside choice frees the shelf.',
         'The shelf looks empty until the bowl is revealed tucked under it.'),
        ('Fixture: Heavy Reflection', 'straighten a hand mirror', 'The mirror is tilted by its heavy reflected fruit while Arda steadies it.',
         'This mirror bears the weight of the objects visible in its reflection.',
         'One tilt adds reflected weight; another removes the counterbalance; Arda chooses an empty reflected wall.',
         'An apparently weightless mirror balances beside the untouched real fruit.')
    ], 1)
]

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        if self.path.endswith('/creative-role/readiness'):
            result = dict(enabled=True, liveVerified=False,
                          roles=[dict(role='IDEA', provider='openai', model='gpt-6-sol', configured=True)],
                          storyProviders=[])
        elif self.path.endswith('/creative-role') and request.get('role') == 'IDEA':
            with LOG.open('a') as stream:
                stream.write(json.dumps(request) + '\n')
            result = dict(role='IDEA', provider='FIXTURE_NO_PROVIDER', model='fixture-no-provider', calls=0,
                          actualCostUsd=0, result=dict(candidates=CANDIDATES),
                          rawProviderResponse=json.dumps(dict(candidates=CANDIDATES)),
                          providerResponseMetadata=dict(requestId='isolated-fixture-receipt-001'))
        else:
            self.send_error(400, 'Only IDEA fixtures and readiness supported; no provider adapter exists')
            return
        raw = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8090), Handler).serve_forever()
