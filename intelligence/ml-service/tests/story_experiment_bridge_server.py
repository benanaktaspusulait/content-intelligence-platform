"""Keep imports warm for the disposable Java contract suite; test-only IPC."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys

bridge=Path(__file__).with_name('story_experiment_bridge.py')
stream=sys.stdin
for line in stream:
    output=io.StringIO();error=None
    try:
        sys.stdin=io.StringIO(line)
        with contextlib.redirect_stdout(output):
            try:runpy.run_path(str(bridge),run_name='__main__')
            except SystemExit as stopped:
                if stopped.code not in (None,0):raise
    except BaseException as failure:
        error=type(failure).__name__+': '+str(failure)
    finally:sys.stdin=stream
    print(json.dumps({'output':output.getvalue(),'error':error}),flush=True)
