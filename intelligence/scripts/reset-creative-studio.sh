#!/usr/bin/env bash
# Local test prompt/workflow reset. Requires Docker and Python 3.9+.
# Planning is read-only on the source DB; backups are restored in network-isolated tmpfs.
# No automatic browser reset, provider calls, render requests, migration or sequence changes.
# From the repository root, first create and review a backed-up deletion plan:
#   ./intelligence/scripts/reset-creative-studio.sh --include-unbound-analysis
# Review target-records.json in the printed backup directory. Then run:
#   ./intelligence/scripts/reset-creative-studio.sh --execute /absolute/path/manifest.json --allow-append-only-test-delete
# Execution asks for the plan's exact confirmation phrase. Changed rows invalidate it.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "$SCRIPT_DIR/../.." "$@" <<'PYTHON'
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

os.umask(0o077)
REPO = Path(sys.argv[1]).resolve()
ERROR_DIRECTORY = None
TARGETS = {
    'public.quality_validations': 'id',
    'public.failed_rules': 'id',
    'public.validation_runs': 'id',
    'public.workflow_repair_sessions': 'id',
    'public.prompt_creative_provenance': 'prompt_version_id',
    'public.post_family_workflow_events': 'id',
    'public.prompt_versions': 'id',
    'public.contents': 'id',
}
# Learning, real video QA, association and edit/render handoff events are protected.
TEST_EVENT_KINDS = {
    'CREATIVE_ROLE', 'STORY_APPROVAL', 'CREATIVE_STUDIO_SESSION',
    'CREATIVE_STUDIO_LIFECYCLE', 'PRODUCTION_SPEC_MIGRATION', 'REVIEW',
    'PRODUCTION_SETTINGS', 'PRODUCTION_REVIEW_DECISION',
    'PRODUCTION_CHARACTER_REFERENCE_BINDING', 'VISUAL_PREPARATION',
    'SECOND_OPINION', 'REPAIR',
}
UUID_TABLES = {'public.post_family_workflow_events', 'public.workflow_repair_sessions'}
SCHEMA_SQL = """SELECT md5(coalesce(string_agg(s, E'\\n' ORDER BY s), '')) FROM (
 SELECT n.nspname||'.'||c.relname||':'||a.attname||':'||format_type(a.atttypid,a.atttypmod)||':'||a.attnotnull s
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
 UNION ALL SELECT conrelid::regclass::text||':'||conname||':'||pg_get_constraintdef(oid) FROM pg_constraint
 UNION ALL SELECT tgrelid::regclass::text||':'||tgname||':'||tgenabled::text||':'||pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal
 UNION ALL SELECT schemaname||'.'||tablename||':'||indexdef FROM pg_indexes WHERE schemaname NOT LIKE 'pg_%'
 UNION ALL SELECT n.nspname||'.'||p.proname||':'||pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN ('public','creative_render','publisher_support') AND p.prokind='f'
) definitions"""
# PostgreSQL reparses some equivalent varchar-array casts during pg_restore.
# Compare portable structure across databases; retain exact DDL hashes for source drift
# and for proving that rehearsal restores the recovery database's own trigger state.
STRUCTURE_SQL = """SELECT md5(coalesce(string_agg(s, E'\\n' ORDER BY s), '')) FROM (
 SELECT n.nspname||'.'||c.relname||':'||a.attname||':'||format_type(a.atttypid,a.atttypmod)||':'||a.attnotnull s
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
 UNION ALL SELECT conrelid::regclass::text||':'||conname||':'||contype::text||':'||convalidated::text||':'||
 CASE WHEN contype IN ('f','p','u') THEN pg_get_constraintdef(oid) ELSE coalesce(conkey::text,'') END FROM pg_constraint
 UNION ALL SELECT tgrelid::regclass::text||':'||tgname||':'||tgenabled::text||':'||pg_get_triggerdef(oid) FROM pg_trigger WHERE NOT tgisinternal
 UNION ALL SELECT schemaname||'.'||tablename||':'||indexname FROM pg_indexes WHERE schemaname NOT LIKE 'pg_%'
) definitions"""


def fail(message):
    raise RuntimeError(message)


def run(args, **kwargs):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        # Do not echo Docker environment variables, stored rows or connection secrets.
        if ERROR_DIRECTORY:
            output = result.stderr.decode(errors='replace') if isinstance(result.stderr, bytes) else result.stderr
            (ERROR_DIRECTORY/'command-error.log').write_text(output or '')
        fail(f'{args[0]} {args[1] if len(args)>1 else ""} failed (exit {result.returncode}). No scope widening is attempted.')
    return result.stdout


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    path.chmod(0o600)


def ident(name):
    return '"' + name.replace('"', '""') + '"'


def table_sql(name):
    return '.'.join(ident(part) for part in name.split('.'))


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def predicate(table, ids):
    if table not in TARGETS:
        fail('Unapproved table in manifest: ' + table)
    for value in ids:
        if table in UUID_TABLES:
            if str(UUID(str(value))) != str(value):
                fail('Noncanonical UUID in allowlist')
        elif not re.fullmatch(r'[1-9][0-9]*', str(value)):
            fail('Invalid numeric ID in allowlist')
    return ident(TARGETS[table]) + ' IN (' + ','.join(literal(x) for x in ids) + ')' if ids else 'FALSE'


def inspect_local():
    context = run(['docker', 'context', 'show'], text=True).strip()
    endpoint = json.loads(run(['docker', 'context', 'inspect', context], text=True))[0]['Endpoints']['docker']['Host']
    if context != 'desktop-linux' or not endpoint.startswith('unix://'):
        fail('Only the verified local Docker Desktop Unix-socket context desktop-linux is supported.')
    source = {}
    for service in ('postgres', 'backend', 'creative-render-service'):
        name = 'intelligence-' + service + '-1'
        d = json.loads(run(['docker', 'inspect', name], text=True))[0]
        labels = d['Config'].get('Labels') or {}
        if labels.get('com.docker.compose.project') != 'intelligence' or labels.get('com.docker.compose.service') != service:
            fail('Unexpected Compose identity: ' + name)
        if Path(labels.get('com.docker.compose.project.working_dir', '/')).resolve() != REPO / 'intelligence':
            fail('Container belongs to a different checkout: ' + name)
        if not d['State']['Running']:
            fail('Required local service is not running: ' + name)
        env = dict(x.split('=', 1) for x in d['Config']['Env'] if '=' in x)
        if service == 'postgres':
            if env.get('POSTGRES_DB') != 'pompom' or env.get('POSTGRES_USER') != 'pompom':
                fail('Only the verified local pompom database/user is supported.')
            source['image_id'] = d['Image']
        else:
            key = 'DB_URL' if service == 'backend' else 'SPRING_DATASOURCE_URL'
            if env.get(key) != 'jdbc:postgresql://postgres:5432/pompom':
                fail('Service points to a different datasource: ' + name)
        source[service] = d['Id']
    return source


def query(sql, container='intelligence-postgres-1'):
    output = run(['docker', 'exec', '-i', container, 'psql', '-U', 'pompom', '-d', 'pompom',
                  '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1'],
                 input='BEGIN READ ONLY;\n' + sql + ';\nCOMMIT;\n', text=True)
    return json.loads('\n'.join(line for line in output.splitlines() if line not in ('BEGIN', 'COMMIT', '')))


def schema_fingerprint(container='intelligence-postgres-1'):
    return query('SELECT to_json(fingerprint) FROM ('+SCHEMA_SQL+') AS fingerprint_result(fingerprint)', container)


def schema_structure(container='intelligence-postgres-1'):
    return query('SELECT to_json(fingerprint) FROM ('+STRUCTURE_SQL+') AS fingerprint_result(fingerprint)', container)


def tables():
    return query("SELECT coalesce(json_agg(name ORDER BY name),'[]') FROM (SELECT table_schema||'.'||table_name name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') AND table_type='BASE TABLE') t")


def inventory(names, scope=None, container='intelligence-postgres-1'):
    parts = []
    for name in names:
        where = ' WHERE NOT (' + predicate(name, scope[name]) + ')' if scope and name in scope else ''
        parts.append("SELECT json_build_object('table'," + literal(name) + ", 'count',count(*),'rows_md5',md5(coalesce(string_agg(md5(to_jsonb(r)::text),'' ORDER BY md5(to_jsonb(r)::text)),''))) data FROM " + table_sql(name) + ' r' + where)
    rows = query('SELECT json_agg(data) FROM (' + ' UNION ALL '.join(parts) + ') inventory', container)
    return {row['table']: row for row in rows}


def rows(name):
    return query("SELECT coalesce(json_agg(to_jsonb(r)),'[]') FROM " + table_sql(name) + ' r')


def discover(include_unbound):
    names = tables()
    if not set(TARGETS).issubset(names):
        fail('Expected workflow schema is absent. Review the schema before adapting this script.')
    scope = {name: [] for name in TARGETS}
    contents = [row for row in rows('public.contents') if row['status'] == 'DRAFT']
    scope['public.contents'] = [row['id'] for row in contents]
    prompts = [row for row in rows('public.prompt_versions') if row['content_id'] in scope['public.contents']]
    scope['public.prompt_versions'] = [row['id'] for row in prompts]
    events = [row for row in rows('public.post_family_workflow_events') if row['kind'] in TEST_EVENT_KINDS]
    scope['public.post_family_workflow_events'] = [row['id'] for row in events]
    scope['public.prompt_creative_provenance'] = [row['prompt_version_id'] for row in rows('public.prompt_creative_provenance') if row['prompt_version_id'] in scope['public.prompt_versions']]
    scope['public.quality_validations'] = [row['id'] for row in rows('public.quality_validations')
        if (row.get('content_id') in scope['public.contents'] and row.get('prompt_version_id') in scope['public.prompt_versions'])
        or (include_unbound and row.get('content_id') is None and row.get('prompt_version_id') is None)]
    scope['public.validation_runs'] = [row['id'] for row in rows('public.validation_runs') if row['prompt_version_id'] in scope['public.prompt_versions']]
    scope['public.failed_rules'] = [row['id'] for row in rows('public.failed_rules') if row['validation_run_id'] in scope['public.validation_runs']]
    scope['public.workflow_repair_sessions'] = [row['id'] for row in rows('public.workflow_repair_sessions') if row['review_id'] in scope['public.post_family_workflow_events']]
    # IDs, candidate/revision identities and payloads are kept privately for operator review.
    manifest_rows = {name: [row for row in rows(name) if row[TARGETS[name]] in scope[name]] for name in TARGETS}
    return names, scope, {'contents': contents, 'prompts': [{'id':x['id'], 'content_id':x['content_id'], 'version_number':x['version_number']} for x in prompts]}, manifest_rows


def leaves(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from leaves(child, path + '[' + str(i) + ']')
    else:
        yield path, value


def protected_references(names, scope):
    hits = []
    content_ids = set(map(str, scope['public.contents']))
    prompt_ids = set(map(str, scope['public.prompt_versions']))
    event_ids = set(scope['public.post_family_workflow_events'])
    existing_contents = set(str(row['id']) for row in rows('public.contents'))
    existing_prompts = set(str(row['id']) for row in rows('public.prompt_versions'))
    existing_videos = set(str(row['id']) for row in rows('public.videos')) if 'public.videos' in names else set()
    for name in names:
        for row in rows(name):
            if name in scope and str(row[TARGETS[name]]) in set(map(str, scope[name])):
                # Test events must not themselves belong to a preserved content/prompt/video.
                if name == 'public.post_family_workflow_events':
                    for path, value in leaves(row):
                        key = re.sub('[^a-z]', '', path.rsplit('.', 1)[-1].lower())
                        protected = (key.endswith('contentid') and str(value) in existing_contents - content_ids)
                        protected = protected or (key.endswith('promptversionid') and str(value) in existing_prompts - prompt_ids)
                        protected = protected or (key.endswith('videoid') and str(value) in existing_videos)
                        if protected:
                            hits.append({'table': name, 'row_id': row['id'], 'identity_path': path, 'reason': 'Target belongs to preserved operational data'})
                continue
            for path, value in leaves(row):
                key = re.sub('[^a-z]', '', path.rsplit('.', 1)[-1].lower())
                hit = (key.endswith('contentid') and str(value) in content_ids) or (key.endswith('promptversionid') and str(value) in prompt_ids)
                if isinstance(value, str):
                    hit = hit or any(uid in value for uid in event_ids)
                    hit = hit or any(match in content_ids for match in re.findall(r'content:(\d+)(?!\d)', value))
                    hit = hit or any(match in prompt_ids for match in re.findall(r'prompt:(\d+)(?!\d)', value))
                if hit:
                    hits.append({'table': name, 'row_id': row.get('id'), 'identity_path': path})
    # Declared foreign keys cover other integer identities and cross-schema relations.
    fks = query("""SELECT coalesce(json_agg(x),'[]') FROM (
      SELECT nc.nspname||'.'||c.relname child, np.nspname||'.'||p.relname parent, k.conname,
       ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY u(id,ord) JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=u.id ORDER BY ord) child_columns,
       ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY u(id,ord) JOIN pg_attribute a ON a.attrelid=p.oid AND a.attnum=u.id ORDER BY ord) parent_columns
      FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace nc ON nc.oid=c.relnamespace
      JOIN pg_class p ON p.oid=k.confrelid JOIN pg_namespace np ON np.oid=p.relnamespace WHERE k.contype='f') x""")
    for fk in fks:
        parent, child = fk['parent'], fk['child']
        if parent not in scope or not scope[parent]:
            continue
        join = ' AND '.join('c.'+ident(a)+'=p.'+ident(b) for a,b in zip(fk['child_columns'], fk['parent_columns']))
        parent_filter = 'p.' + predicate(parent, scope[parent])
        child_filter = ' AND NOT (c.' + predicate(child, scope[child]) + ')' if child in scope and scope[child] else ''
        count = query('SELECT count(*) FROM '+table_sql(child)+' c JOIN '+table_sql(parent)+' p ON '+join+' WHERE '+parent_filter+child_filter)
        if count:
            hits.append({'foreign_key': fk['conname'], 'protected_child': child, 'target_parent': parent, 'count': count})
    return hits


def guard(name, expected):
    if type(expected['count']) is not int or expected['count'] < 0 or not re.fullmatch(r'[0-9a-f]{32}', expected['rows_md5']):
        fail('Invalid inventory fingerprint/count: ' + name)
    return "DO $guard$ DECLARE n bigint; h text; BEGIN SELECT count(*),md5(coalesce(string_agg(md5(to_jsonb(r)::text),'' ORDER BY md5(to_jsonb(r)::text)),'')) INTO n,h FROM " + table_sql(name) + ' r; IF n <> ' + str(expected['count']) + ' OR h <> ' + literal(expected['rows_md5']) + ' THEN RAISE EXCEPTION ' + literal('Inventory mismatch: '+name) + '; END IF; END $guard$;'


def cleanup_sql(manifest):
    scope, before, after = manifest['allowlists'], manifest['before'], manifest['expected_after']
    if set(scope) != set(TARGETS) or set(before) != set(after):
        fail('Manifest table allowlist is invalid')
    sql = ['\\set ON_ERROR_STOP on', 'BEGIN;', "SET LOCAL lock_timeout='5s';", "SET LOCAL statement_timeout='60s';",
           'LOCK TABLE '+','.join(table_sql(name) for name in sorted(before))+' IN SHARE ROW EXCLUSIVE MODE;',
           "DO $guard$ BEGIN IF current_database()<>'pompom' THEN RAISE EXCEPTION 'Database mismatch'; END IF; END $guard$;",
           'DO $guard$ BEGIN IF ('+SCHEMA_SQL+') <> '+literal(manifest['schema_md5'])+" THEN RAISE EXCEPTION 'Schema/trigger drift'; END IF; END $guard$;"]
    sql += [guard(name, before[name]) for name in sorted(before)]
    for name, key in TARGETS.items():
        ids = scope[name]
        if not ids:
            continue
        if name == 'public.prompt_creative_provenance':
            sql.append("DO $guard$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='public.prompt_creative_provenance'::regclass AND tgname='prompt_creative_provenance_append_only' AND tgenabled='O') THEN RAISE EXCEPTION 'Provenance trigger is not enabled'; END IF; END $guard$;")
            sql.append('ALTER TABLE public.prompt_creative_provenance DISABLE TRIGGER prompt_creative_provenance_append_only;')
        sql.append('DO $delete$ DECLARE n bigint; BEGIN DELETE FROM '+name+' WHERE '+predicate(name, ids)+'; GET DIAGNOSTICS n=ROW_COUNT; IF n <> '+str(len(ids))+' THEN RAISE EXCEPTION '+literal('Deletion count mismatch: '+name)+'; END IF; RAISE NOTICE '+literal('Deleted % allowlisted rows from '+name)+',n; END $delete$;')
        if name == 'public.prompt_creative_provenance':
            sql.append('ALTER TABLE public.prompt_creative_provenance ENABLE TRIGGER prompt_creative_provenance_append_only;')
    sql += [guard(name, after[name]) for name in sorted(after)]
    sql += ['DO $guard$ BEGIN IF ('+SCHEMA_SQL+') <> '+literal(manifest['schema_md5'])+" THEN RAISE EXCEPTION 'Schema/trigger not restored'; END IF; END $guard$;", 'COMMIT;']
    return '\n'.join(sql)+'\n'


def backup_and_rehearse(directory, manifest):
    archive = directory/'pompom.dump'
    with archive.open('wb') as output:
        result = subprocess.run(['docker','exec','intelligence-postgres-1','pg_dump','-U','pompom','-d','pompom','-Fc'], stdout=output, stderr=subprocess.PIPE)
    if result.returncode:
        fail('Backup failed; no cleanup allowed')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    with archive.open('rb') as stream:
        run(['docker','exec','-i','intelligence-postgres-1','pg_restore','--file=/dev/null'], stdin=stream)
    if inventory(list(manifest['before'])) != manifest['before'] or schema_fingerprint() != manifest['schema_md5']:
        fail('Source changed while backing up. Generate a fresh plan.')
    name = 'pompom-reset-check-'+uuid4().hex[:12]
    try:
        run(['docker','run','-d','--name',name,'--network','none','--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=2147483648',
             '-e','POSTGRES_HOST_AUTH_METHOD=trust','-e','POSTGRES_USER=pompom','-e','POSTGRES_DB=pompom',manifest['environment']['image_id']])
        for attempt in range(60):
            # initdb briefly starts a Unix-socket-only server, then restarts it.
            # TCP readiness avoids restoring into that temporary startup server.
            ready = subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','pompom','-d','pompom'], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            fail('Recovery container did not become ready')
        with archive.open('rb') as stream:
            run(['docker','exec','-i',name,'pg_restore','-U','pompom','-d','pompom','--exit-on-error'], stdin=stream)
        if inventory(list(manifest['before']), container=name) != manifest['before']:
            fail('Restored backup does not match source row counts and content fingerprints')
        if schema_structure(name) != manifest['schema_structure_md5']:
            fail('Restored backup columns, constraints, foreign keys, indexes or triggers do not match source')
        rehearsal = dict(manifest, schema_md5=schema_fingerprint(name))
        sql = cleanup_sql(rehearsal)
        with (directory/'isolated-rehearsal.log').open('w') as log:
            result = subprocess.run(['docker','exec','-i',name,'psql','-U','pompom','-d','pompom','-X','-v','ON_ERROR_STOP=1'], input=sql, text=True, stdout=log, stderr=log)
        if result.returncode or inventory(list(manifest['before']), container=name) != manifest['expected_after']:
            fail('Isolated cleanup rehearsal failed; inspect private isolated-rehearsal.log. Source was not changed.')
    finally:
        # Only this randomly named temporary container is removed; never remove any volume.
        subprocess.run(['docker','stop',name], capture_output=True)
        subprocess.run(['docker','rm',name], capture_output=True)
    return {'archive':str(archive),'sha256':checksum,'restore_verified':True,'cleanup_rehearsal_verified':True,
            'recovered_schema_md5':rehearsal['schema_md5'],'portable_schema_structure_md5':manifest['schema_structure_md5']}


def digest(manifest):
    return hashlib.sha256(json.dumps({k:v for k,v in manifest.items() if k not in ('digest','approval_phrase')}, sort_keys=True).encode()).hexdigest()


def main():
    global ERROR_DIRECTORY
    parser = argparse.ArgumentParser(prog='reset-creative-studio.sh', description='Local Creative Studio TEST prompt reset; default is a backed-up, restore-verified dry run. No source rows are deleted until a manifest is explicitly approved.')
    parser.add_argument('--execute', type=Path, metavar='MANIFEST', help='Execute a previously reviewed manifest; prompts for its exact approval phrase')
    parser.add_argument('--include-unbound-analysis', action='store_true', help='Also PROPOSE standalone quality_validations; operator must confirm these are test data')
    parser.add_argument('--allow-append-only-test-delete', action='store_true', help='Explicit exception for ONLY allowlisted local test prompt_creative_provenance rows')
    parser.add_argument('--output', type=Path, help='New backup/report directory OUTSIDE this repository')
    args = parser.parse_args(sys.argv[2:])
    if args.execute and (args.output or args.include_unbound_analysis):
        parser.error('Execution uses the frozen manifest; generate a new dry run to change scope.')
    environment = inspect_local()
    if args.execute:
        path = args.execute.resolve()
        if path.is_relative_to(REPO):
            fail('Manifest/backup must be outside the repository')
        ERROR_DIRECTORY = path.parent
        manifest = json.loads(path.read_text())
        if manifest.get('format') != 'pompom-test-reset-v1' or manifest.get('digest') != digest(manifest):
            fail('Manifest changed or unsupported format. Generate a new dry run.')
        if environment != manifest['environment']:
            fail('Container/environment identity changed. Generate a fresh plan.')
        if tables() != sorted(manifest['before']) or inventory(sorted(manifest['before'])) != manifest['before']:
            fail('Records changed since dry run. Generate a fresh plan; never widen scope automatically.')
        if schema_fingerprint() != manifest['schema_md5']:
            fail('Schema/trigger definitions changed since dry run')
        backup = manifest['backup']
        if not backup['restore_verified'] or not backup['cleanup_rehearsal_verified'] or hashlib.sha256(Path(backup['archive']).read_bytes()).hexdigest() != backup['sha256']:
            fail('Backup verification/checksum failed')
        hits = protected_references(sorted(manifest['before']), manifest['allowlists'])
        if hits:
            fail('Protected references now exist. Abort; create a new reviewed plan.')
        if not manifest['row_count']:
            print('No allowlisted test records remain. Nothing deleted.')
            return
        if manifest['allowlists']['public.prompt_creative_provenance'] and not args.allow_append_only_test_delete:
            fail('Append-only test rows require --allow-append-only-test-delete, plus the explicit scope confirmation.')
        print('Shared local DB: pompom. Confirm every manifest ID is disposable TEST data.')
        print('Exact deletion counts:', {k:len(v) for k,v in manifest['allowlists'].items()})
        print('Type exactly: '+manifest['approval_phrase'])
        approval = os.environ.get('POMPOM_RESET_APPROVAL')
        if approval is None:
            try:
                with open('/dev/tty', 'r+') as terminal:
                    terminal.write('Approval: '); terminal.flush()
                    approval = terminal.readline().strip()
            except OSError as error:
                fail('Approval terminal unavailable. Set POMPOM_RESET_APPROVAL to the exact printed phrase; no source cleanup executed.')
        if approval != manifest['approval_phrase']:
            fail('Approval did not match. No source cleanup executed.')
        sql = cleanup_sql(manifest)
        (path.parent/'approved-cleanup.sql').write_text(sql)
        with (path.parent/'execution.log').open('w') as log:
            result = subprocess.run(['docker','exec','-i','intelligence-postgres-1','psql','-U','pompom','-d','pompom','-X','-v','ON_ERROR_STOP=1'], input=sql, text=True, stdout=log, stderr=log)
        if result.returncode:
            fail('Cleanup transaction aborted. No broader deletion attempted; inspect private execution.log.')
        after = inventory(sorted(manifest['before']))
        write(path.parent/'after.json', after)
        if after != manifest['expected_after'] or schema_fingerprint() != manifest['schema_md5']:
            fail('Post-commit verification mismatch. Preserve backup/logs and investigate; do not run cleanup again.')
        write(path.parent/'execution-result.json', {'status':'EXECUTED','deleted':manifest['row_count'],'schema_and_triggers_preserved':True,'protected_rows_unchanged':True})
        # Browser changes require an explicit browser action. Never clear auth or all localStorage.
        content = list(map(str,manifest['allowlists']['public.contents']))
        prompts = list(map(str,manifest['allowlists']['public.prompt_versions']))
        js = 'const contentIds = new Set('+json.dumps(content)+');\nconst promptIds = new Set('+json.dumps(prompts)+');\n'
        js += "for (const storage of [localStorage, sessionStorage]) { for (const key of Object.keys(storage)) { const m = key.match(/^pompom-(?:studio-location|preparation-tab):([0-9]+):([0-9]+)(?::.*)?$/); if (key === 'pompom.creative-studio.v1' || (m && contentIds.has(m[1]) && promptIds.has(m[2]))) storage.removeItem(key); } }\nlocation.assign('/quality/new');\n"
        (path.parent/'browser-reset.js').write_text(js)
        print(f'EXECUTED: {manifest["row_count"]} exact test rows deleted. Protected data/schema/trigger state verified.')
        print('Browser state is not automatically cleared. On localhost:4200 only, run the reviewed browser-reset.js in DevTools; it preserves auth/unrelated preferences.')
        print('Reports/backup: '+str(path.parent))
        return
    directory = (args.output or Path.home()/'.local/share/pompom/creative-studio-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')).resolve()
    if directory.is_relative_to(REPO):
        fail('Backups must be outside the repository')
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    ERROR_DIRECTORY = directory
    names, scope, identities, target_rows = discover(args.include_unbound_analysis)
    before = inventory(names)
    expected = inventory(names, scope)
    hits = protected_references(names, scope)
    write(directory/'protected-references.json', hits)
    write(directory/'target-records.json', target_rows)
    if hits:
        fail('Protected/shared references found. No deletion plan authorized. Inspect '+str(directory/'protected-references.json'))
    manifest = {'format':'pompom-test-reset-v1','status':'PROPOSED','created_utc':datetime.now(timezone.utc).isoformat(),
                'environment':environment,'allowlists':scope,'identities':identities,'before':before,'expected_after':expected,
                'schema_md5':schema_fingerprint(),'schema_structure_md5':schema_structure(),'row_count':sum(map(len,scope.values())),
                'include_unbound_analysis':args.include_unbound_analysis}
    print('PROPOSED local TEST scope:', {k:len(v) for k,v in scope.items()})
    print('Titles do not prove ownership. Review target-records.json and approve only disposable test IDs.')
    print('Creating full backup, restoring it without network/ports, and rehearsing exact deletions...')
    manifest['backup'] = backup_and_rehearse(directory, manifest)
    manifest['digest'] = digest(manifest)
    manifest['approval_phrase'] = 'DELETE '+str(manifest['row_count'])+' LOCAL TEST ROWS '+manifest['digest'][:12]
    write(directory/'manifest.json', manifest)
    (directory/'proposed-cleanup.sql').write_text(cleanup_sql(manifest))
    print('DRY RUN COMPLETE. Source DB unchanged. Backup restored and deletion rehearsal verified.')
    print('Manifest: '+str(directory/'manifest.json'))
    print('Execute reviewed scope: '+str(REPO/'intelligence/scripts/reset-creative-studio.sh')+' --execute '+str(directory/'manifest.json')+(' --allow-append-only-test-delete' if scope['public.prompt_creative_provenance'] else ''))


if __name__ == '__main__':
    # Ensure temporary recovery containers are cleaned up on ordinary interruptions.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    try:
        main()
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print('STOP: '+str(error), file=sys.stderr)
        sys.exit(1)
PYTHON
