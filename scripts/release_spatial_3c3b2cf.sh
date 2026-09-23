#!/usr/bin/bash
# Approved release only. No source edits, secret provisioning or paid image calls.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
umask 077
if [[ $# -eq 1 && $1 == --self-test ]]; then
    : # Definitions and isolated tests only; the production procedure is never entered.
elif [[ $# -eq 0 ]]; then
    [[ $EUID -eq 0 ]] || { printf 'ERROR: local root execution required.\n' >&2; exit 1; }
else
    printf 'Usage: %s [--self-test]\n' "$0" >&2; exit 2
fi
exec /home/administrator/ai-rag-chatbot/venv/bin/python -B - "$@" <<'PY'
import datetime as dt
import fcntl
import hashlib
import http.client as http_client
import io
import json
import os
import pathlib
import pwd
import re
import shutil
import signal
import socket
import ssl
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

RELEASE_SHA = '3c3b2cf068dc2d5eda99242150fe92f5b84d5db3'
ROLLBACK_SHA = '4223cc2a4e7629283b1310e14a412db419baec6b'
GOLD = 'e26dd57514ad5c23eb07aab87b76e4bf65126bca'
REPO = pathlib.Path('/home/administrator/ai-rag-chatbot')
ROOT = pathlib.Path('/var/www/trident-ai/releases')
NEW = ROOT / RELEASE_SHA
OLD = ROOT / ROLLBACK_SHA
ARCHIVE = pathlib.Path('/tmp/trident-spatial-release-3c3b2cf068dc.CcX6T7/release.tar.gz')
ARCHIVE_HASH = '3814362da81b558469b9c36a3424c8ccf6d9754723ea6d644735c20c03e61e33'
ENV_FILE = pathlib.Path('/etc/trident/trident-ai.env')
SITES = [pathlib.Path('/etc/nginx/sites-available/trident-ai'), pathlib.Path('/etc/nginx/sites-enabled/trident-ai')]
UNITS = ['trident-backend.service', 'trident-knowledge-worker.service']
DROPIN = '90-trident-spatial-release.conf'
DOMAIN = 'trident-ai.org'
STAMP = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'
BACKUP = pathlib.Path('/var/backups/trident-ai/releases') / f'{STAMP}-{RELEASE_SHA[:12]}'
# Preserve the recovered runtime and the already verified backup, never recreate them.
PRESERVED_BACKUP = pathlib.Path('/var/backups/trident-ai/releases/20260922T212509Z-558456-3c3b2cf068dc')
ROLLBACK_RUNTIME = ROOT / f'.backend-rollback-{ROLLBACK_SHA}-20260922T212509Z-558456'
READINESS_TIMEOUT = 90
OPS_SCRIPT_PATH = 'scripts/release_spatial_3c3b2cf.sh'
OPERATIONAL_HEAD = None
SERVICE_USER = pwd.getpwnam('administrator')
STATE = dict(backup=False, stopped=False, migration=False, nginx=False, switched=False, success=False)
STEP = 'preflight'
CFG = None
ENGINE = None
RUNTIME_ENV = None
ASSETS = None
PROTECTED = {}
AUTHENTICATED = False
COOKIE = None
LOG_OFFSET = None
ACTIVE_SHA = 'UNVERIFIED'
CANDIDATE = None

class GateError(Exception): pass

def gate(ok, label):
    if not ok: raise GateError(label)

def phase(label):
    global STEP
    STEP = label
    print('PHASE=' + label, flush=True)

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def as_service_user():
    os.initgroups(SERVICE_USER.pw_name, SERVICE_USER.pw_gid)
    os.setgid(SERVICE_USER.pw_gid)
    os.setuid(SERVICE_USER.pw_uid)

def run(args, *, cwd=None, env=None, user=False, timeout=180, input=None):
    # Capture, never echo command output which might contain credentials.
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env, input=input,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
        preexec_fn=as_service_user if user else None)
    if result.returncode:
        raise GateError(f'{STEP}: {pathlib.Path(str(args[0])).name} exit={result.returncode}; output withheld for credential safety')
    return result.stdout

def git(*args):
    output = run(['/usr/bin/git', '-c', f'safe.directory={REPO}', '-C', REPO, *args]).decode()
    return output if '-z' in args else output.strip()

def verify_clean_checkout():
    git('diff', '--exit-code'); git('diff', '--cached', '--exit-code'); git('diff', '--check')
    # Existing visual evidence is intentionally untracked, never deployable source.
    untracked = git('ls-files', '--others', '--exclude-standard', '-z').split('\0')
    gate(all(not name or name.startswith('visual-review/') for name in untracked), 'Unexpected untracked source')

def capture_operational_head():
    gate(git('branch', '--show-current') == 'trident-ai', 'Wrong branch')
    head = git('rev-parse', 'HEAD')
    gate(re.fullmatch('[0-9a-f]{40}', head) is not None, 'Invalid operational HEAD')
    gate(head == git('rev-parse', 'origin/trident-ai'), 'Operational HEAD is not synchronized with origin/trident-ai')
    git('merge-base', '--is-ancestor', RELEASE_SHA, head)
    changed = set(filter(None, git('diff', '--no-renames', '--name-only', '-z', RELEASE_SHA, head, '--').split('\0')))
    gate(changed == {OPS_SCRIPT_PATH}, 'Committed operational delta exceeds release-script allowlist')
    verify_clean_checkout()
    return head

def unit_property(unit, key):
    return run(['/usr/bin/systemctl', 'show', unit, '-p', key, '--value']).decode().strip()

def service_env(pid):
    raw = pathlib.Path(f'/proc/{pid}/environ').read_bytes()
    return dict(part.decode().split('=', 1) for part in raw.split(b'\0') if b'=' in part)

def runtime_env(sha):
    env = dict(RUNTIME_ENV)
    for name in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'): env.pop(name, None)
    env.update(TRIDENT_BUILD_SHA=sha, TRIDENT_IMAGE_PROVIDER='disabled', PYTHONDONTWRITEBYTECODE='1',
        TRIDENT_DATABASE_URL=CFG['database'], TRIDENT_DOCUMENTS_PATH=CFG['documents'],
        TRIDENT_VECTOR_DB_PATH=CFG['vectors'], TRIDENT_IMAGES_PATH=CFG['images'])
    return env

def configuration(env, root=REPO):
    code = '''import json, hashlib
from pathlib import Path
from app.core.config import settings as s
excluded={'build_sha','documents_path','vector_db_path','images_path','image_provider','image_model','image_timeout_seconds'}
fingerprint=hashlib.sha256((json.dumps(s.model_dump(mode='json', exclude=excluded),sort_keys=True)+s.openai_key()).encode()).hexdigest()
print(json.dumps(dict(database=s.database_url, documents=str(s.documents_path.resolve()), vectors=str(s.vector_db_path.resolve()), images=str((getattr(s,'images_path',None) or s.documents_path/'nova-images').resolve()), environment=s.environment, security=s.security_mode, issuer=s.oidc_issuer, client=s.oidc_client_id, redirect=s.oidc_redirect_uri, logout=s.oidc_post_logout_redirect_uri, fingerprint=fingerprint)))
'''
    return json.loads(run([root/'venv/bin/python', '-c', code], cwd=root, env=env, user=True))

class OriginHTTPS(http_client.HTTPSConnection):
    def connect(self):
        raw = socket.create_connection(('127.0.0.1', 443), timeout=self.timeout)
        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=DOMAIN)

def http(path, expected=200, *, public=False, method='GET', payload=None, cookie=None):
    # No redirects followed, no tokens/body printed. Query tag scopes Nginx log checks.
    connection = (http_client.HTTPSConnection if public else OriginHTTPS)(DOMAIN, timeout=20)
    headers = {'Host': DOMAIN, 'Cache-Control': 'no-cache', 'Connection': 'close', 'X-Request-ID': 'release-' + STAMP}
    if cookie: headers['Cookie'] = cookie
    body = None
    if payload is not None:
        body = json.dumps(payload).encode(); headers['Content-Type'] = 'application/json'
    separator = '&' if '?' in path else '?'
    try:
        connection.request(method, path + separator + 'trident_release_probe=' + STAMP, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read(32 * 1024 * 1024)
        gate(response.status == expected, f'HTTP {response.status} expected {expected}: {path.split("?")[0]}')
        return data, dict(response.getheaders())
    finally: connection.close()

def json_http(path, **kwargs): return json.loads(http(path, **kwargs)[0])

def revision():
    with ENGINE.connect() as db: return db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()

def nginx_check(save=False):
    result = subprocess.run(['/usr/sbin/nginx', '-T'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    gate(result.returncode == 0, 'nginx -T failed')
    warnings = result.stderr.decode(errors='replace')
    gate(not re.search(r'conflicting server name "(?:www\.)?trident-ai\.org"', warnings), 'Conflicting production Nginx vhosts')
    config = result.stdout.decode()
    gate(config.count('server_name trident-ai.org www.trident-ai.org;') == 1, 'Unexpected HTTP vhost count')
    gate(config.count('server_name trident-ai.org;') == 1, 'Unexpected HTTPS production vhost count')
    gate(config.count('server_name www.trident-ai.org;') == 1, 'Unexpected HTTPS alias vhost count')
    if save: (BACKUP/'nginx-effective.txt').write_bytes(result.stdout)
    run(['/usr/sbin/nginx', '-t'])
    return config

def frozen_tree(path):
    # Runtime code/dependencies are read-only to service identity; data paths stay external.
    for base, directories, files in os.walk(path):
        os.chown(base, 0, 0); os.chmod(base, 0o755)
        for name in files:
            entry = pathlib.Path(base)/name
            if entry.is_symlink(): continue
            executable = bool(entry.stat().st_mode & 0o111)
            os.chown(entry, 0, 0); os.chmod(entry, 0o755 if executable else 0o644)

def extract_checked(archive, destination):
    with tarfile.open(archive, 'r:*') as tar:
        members = tar.getmembers()
        for member in members:
            p = pathlib.PurePosixPath(member.name)
            gate(not p.is_absolute() and '..' not in p.parts, 'Archive path traversal')
            gate(member.isfile() or member.isdir(), 'Unexpected link/special file in release archive')
            gate(not any(x in {'node_modules', 'visual-review', '.env', '.env.production', '.env.local'} for x in p.parts), 'Forbidden release entry')
        tar.extractall(destination, members=members, filter='data')

def verify_frontend(root):
    manifest = json.loads((root/'FRONTEND_MANIFEST.json').read_text())
    dist = root/'frontend/dist'
    expected = set()
    for item in manifest['files']:
        rel = pathlib.PurePosixPath(item['path'])
        gate(not rel.is_absolute() and '..' not in rel.parts, 'Invalid frontend manifest path')
        file = dist/rel
        gate(file.is_file() and not file.is_symlink(), 'Missing frontend artifact')
        gate(file.stat().st_size == item['bytes'] and digest(file) == item['sha256'], 'Frontend checksum mismatch')
        expected.add(item['path'])
    actual = {p.relative_to(dist).as_posix() for p in dist.rglob('*') if p.is_file()}
    gate(actual == expected, 'Unexpected frontend artifact')
    return sorted(set(re.findall(r'(?:src|href)="(/assets/[^"?]+)"', (dist/'index.html').read_text())))

def verify_source(root, sha):
    tree = run(['/usr/bin/git', '-c', f'safe.directory={REPO}', '-C', REPO, 'ls-tree', '-rz', sha])
    for record in tree.split(b'\0'):
        if not record: continue
        meta, name = record.split(b'\t', 1)
        mode, kind, object_id = meta.split()
        gate(kind == b'blob' and mode in (b'100644', b'100755'), 'Unsupported source tree entry')
        target = root/name.decode()
        gate(target.is_file() and not target.is_symlink(), 'Release source file missing')
        content = target.read_bytes()
        computed = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        gate(computed == object_id.decode(), 'Release source differs from approved SHA')

def archive_directory(source, target):
    run(['/usr/bin/tar', '--acls', '--xattrs', '-czf', target, '-C', source.parent, source.name], timeout=1800)
    run(['/usr/bin/gzip', '-t', target], timeout=1800)

def backup_database():
    url = make_url(CFG['database'])
    if url.get_backend_name() == 'postgresql':
        gate(url.host in (None, '', 'localhost', '127.0.0.1', '::1') or url.host.startswith('/var/run/postgresql'), 'Remote database mutation is not authorized')
        pg = dict(os.environ)
        for key in list(pg):
            if key.startswith('PG'): pg.pop(key)
        pg.update(PGHOST=url.host or '/var/run/postgresql', PGPORT=str(url.port or 5432),
            PGDATABASE=url.database or '', PGUSER=url.username or SERVICE_USER.pw_name, PGPASSWORD=url.password or '', PGCONNECT_TIMEOUT='10')
        gate(not url.query or set(url.query) <= {'sslmode'}, 'Unreviewed PostgreSQL connection options')
        if 'sslmode' in url.query: pg['PGSSLMODE'] = str(url.query['sslmode'])
        with (BACKUP/'database.dump').open('wb') as output:
            dumped = subprocess.run(['/usr/bin/pg_dump', '--format=custom', '--no-owner', '--no-privileges'],
                cwd=REPO, env=pg, preexec_fn=as_service_user, stdout=output, stderr=subprocess.PIPE, timeout=1800)
        gate(dumped.returncode == 0, 'pg_dump failed; credential-bearing output withheld')
        toc = run(['/usr/bin/pg_restore', '--list', BACKUP/'database.dump'])
        gate(b'alembic_version' in toc and b'workspaces' in toc, 'Database backup lacks required tables')
        run(['/usr/bin/pg_restore', '--file=/dev/null', BACKUP/'database.dump'], timeout=1800)
    elif url.get_backend_name() == 'sqlite':
        import sqlite3
        gate(url.database and url.database != ':memory:' and pathlib.Path(url.database).is_absolute(), 'Non-durable SQLite database')
        with sqlite3.connect(f'file:{url.database}?mode=ro', uri=True) as src, sqlite3.connect(BACKUP/'database.sqlite') as dst:
            src.backup(dst)
            gate(dst.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite backup failed integrity check')
            gate(dst.execute('SELECT version_num FROM alembic_version').fetchone()[0] == '0010_document_lifecycle', 'SQLite backup revision mismatch')
    else: raise GateError('Unsupported database engine: no mutation performed')

def runtime_command(root, unit):
    gate(unit in UNITS, 'Unexpected runtime unit')
    return [str(root/'venv/bin/python'), '-m'] + (
        ['uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--proxy-headers', '--forwarded-allow-ips=127.0.0.1']
        if unit == UNITS[0] else ['app.knowledge.worker', '--poll-seconds', '2'])

def render_runtime_dropins(root, sha):
    gate((root, sha) in ((NEW, RELEASE_SHA), (ROLLBACK_RUNTIME, ROLLBACK_SHA)), 'Unapproved runtime directory/SHA')
    gate(root.is_absolute() and root.resolve() == root and re.fullmatch(r'/[A-Za-z0-9_./-]+', str(root)), 'Unsafe WorkingDirectory')
    extra = [f'TRIDENT_BUILD_SHA={sha}', 'TRIDENT_IMAGE_PROVIDER=disabled', 'PYTHONDONTWRITEBYTECODE=1',
        f'TRIDENT_DOCUMENTS_PATH={CFG["documents"]}', f'TRIDENT_VECTOR_DB_PATH={CFG["vectors"]}', f'TRIDENT_IMAGES_PATH={CFG["images"]}']
    # Database/auth/secrets continue to come exclusively from the existing EnvironmentFile.
    rendered = {}
    for unit in UNITS:
        command = runtime_command(root, unit)
        quote = lambda s: json.dumps(s.replace('%', '%%'))
        # WorkingDirectory is NOT parsed like ExecStart: no shell-style quotes.
        rendered[unit] = '[Service]\nWorkingDirectory=' + str(root) + '\nExecStart=\nExecStart=/usr/bin/env -u PYTHONPATH -u PYTHONHOME -u VIRTUAL_ENV ' + ' '.join(map(quote, extra+command)) + '\n'
    return rendered

def verify_runtime_dropins(rendered):
    # Load base units + proposed overrides in isolation, never contact/reload PID 1.
    with tempfile.TemporaryDirectory(prefix='trident-systemd-verify-') as temporary:
        directory = pathlib.Path(temporary)
        for unit in UNITS:
            fragment = pathlib.Path(unit_property(unit, 'FragmentPath'))
            shutil.copy2(fragment, directory/unit)
            dropins = directory/(unit+'.d'); dropins.mkdir()
            for original in unit_property(unit, 'DropInPaths').split():
                path = pathlib.Path(original)
                if path.name != DROPIN: shutil.copy2(path, dropins/path.name)
            (dropins/DROPIN).write_text(rendered[unit])
        env = dict(os.environ)
        env['SYSTEMD_UNIT_PATH'] = str(directory) + ':/usr/local/lib/systemd/system:/usr/lib/systemd/system:/lib/systemd/system'
        result = subprocess.run(['/usr/bin/systemd-analyze', 'verify', '--man=no', *(str(directory/unit) for unit in UNITS)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        gate(result.returncode == 0 and not result.stderr.strip(), 'Proposed systemd units failed isolated verification')

def write_runtime_dropins(root, sha):
    rendered = render_runtime_dropins(root, sha)
    verify_runtime_dropins(rendered)
    for unit, content in rendered.items():
        directory = pathlib.Path('/etc/systemd/system')/(unit+'.d')
        directory.mkdir(mode=0o755, exist_ok=True)
        path = directory/DROPIN
        path.write_text(content); path.chmod(0o644)
    run(['/usr/bin/systemctl', 'daemon-reload'])

def restore_runtime_dropins():
    # Restore the exact healthy pre-attempt overrides, not stale checkout settings.
    saved = {unit: (BACKUP/(unit+'.d')/DROPIN) for unit in UNITS}
    verify_runtime_dropins({unit: path.read_text() for unit, path in saved.items()})
    for unit, path in saved.items():
        shutil.copy2(path, pathlib.Path('/etc/systemd/system')/(unit+'.d')/DROPIN)
    run(['/usr/bin/systemctl', 'daemon-reload'])

def process_identity(root, sha, unit):
    run(['/usr/bin/systemctl', 'is-active', '--quiet', unit])
    pid = int(unit_property(unit, 'MainPID'))
    gate(pid > 1, unit + ': missing MainPID')
    proc = pathlib.Path(f'/proc/{pid}')
    gate(unit_property(unit, 'WorkingDirectory') == str(root), unit + ': configured cwd mismatch')
    gate((proc/'cwd').resolve(strict=True) == root, unit + ': live process cwd mismatch')
    command = [part.decode() for part in (proc/'cmdline').read_bytes().split(b'\0') if part]
    gate(command == runtime_command(root, unit), unit + ': live process command mismatch')
    env = service_env(pid)
    gate(env.get('TRIDENT_BUILD_SHA') == sha, unit + ': process build identity mismatch')
    gate(env.get('TRIDENT_IMAGE_PROVIDER') == 'disabled', unit + ': image provider must remain disabled')
    gate(int(unit_property(unit, 'MainPID')) == pid, unit + ': MainPID changed during verification')
    return pid

def direct_health(suffix):
    connection = http_client.HTTPConnection('127.0.0.1', 8000, timeout=5)
    try:
        connection.request('GET', '/health/' + suffix, headers={'Host': DOMAIN, 'Connection': 'close'})
        response = connection.getresponse()
        gate(response.status == 200, f'Direct /health/{suffix} HTTP {response.status}, expected 200')
        return json.loads(response.read(65536))
    finally: connection.close()

def migrate(direction):
    args = [NEW/'venv/bin/python', '-m', 'alembic']
    args += ['upgrade', '0011_workspace_images'] if direction == 'up' else ['-x', 'allow_empty_image_downgrade=yes', 'downgrade', '0010_document_lifecycle']
    run(args, cwd=NEW, env=runtime_env(RELEASE_SHA), user=True, timeout=300)

def wait_backend(root, sha, schema, *, include_worker=True):
    gate(READINESS_TIMEOUT >= 30, 'Unsafe readiness timeout')
    deadline = time.monotonic() + READINESS_TIMEOUT
    last_failure = 'not checked'
    while True:
        try:
            units = UNITS if include_worker else UNITS[:1]
            pids = {unit: process_identity(root, sha, unit) for unit in units}
            live = direct_health('live')
            ready = direct_health('ready')
            build = direct_health('build')
            gate(live['status'] == 'ok' and ready['status'] == 'ready', 'Backend not ready')
            gate(build['build_sha'] == sha and build['migration_revision'] == schema and build['migration_head'] == schema, 'Backend SHA/schema mismatch')
            gate(build['environment'] == 'production' and build['security_mode'] == 'oidc', 'Production security mode changed')
            if ENGINE is not None: gate(revision() == schema, 'Database revision differs from health identity')
            for unit in units:
                gate(process_identity(root, sha, unit) == pids[unit], 'Runtime restarted during health checks')
            return
        except (GateError, OSError, ValueError, KeyError, http_client.HTTPException) as error:
            last_failure = str(error) if isinstance(error, GateError) else type(error).__name__
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise GateError(f'Backend readiness/identity timeout ({READINESS_TIMEOUT}s): {last_failure}')
        time.sleep(min(2, remaining))

def wait_worker(root, sha):
    deadline = time.monotonic() + READINESS_TIMEOUT
    last_failure = 'not checked'
    while True:
        try:
            pid = process_identity(root, sha, UNITS[1])
            gate(process_identity(root, sha, UNITS[1]) == pid, 'Worker restarted during identity checks')
            return
        except (GateError, OSError, ValueError) as error:
            last_failure = str(error) if isinstance(error, GateError) else type(error).__name__
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise GateError(f'Worker identity timeout ({READINESS_TIMEOUT}s): {last_failure}')
        time.sleep(min(2, remaining))

def activate_runtime(root, sha, schema):
    # Caller verified/wrote drop-ins and completed daemon-reload before entering.
    gate(ENGINE is not None and revision() == schema, 'Database migration must complete before activation')
    run(['/usr/bin/systemctl', 'start', UNITS[0]])
    wait_backend(root, sha, schema, include_worker=False)
    run(['/usr/bin/systemctl', 'start', UNITS[1]])
    wait_worker(root, sha)
    # Recheck backend READY/build/schema AND both identities before frontend switch.
    wait_backend(root, sha, schema)

def wait_frontend(root):
    index = (root/'frontend/dist/index.html').read_bytes()
    assets = sorted(set(re.findall(r'(?:src|href)="(/assets/[^"?]+)"', index.decode())))
    gate(assets, 'Frontend entry assets missing')
    for attempt in range(15):
        try:
            gate(http('/')[0] == index, 'Homepage has not converged')
            for asset in assets:
                gate(http(asset)[0] == (root/'frontend/dist'/asset.lstrip('/')).read_bytes(), 'Served entry asset mismatch')
            return
        except (GateError, OSError):
            if attempt == 14: raise GateError('Nginx index/asset convergence exhausted')
            time.sleep(2)

def restore_sites():
    for i, path in enumerate(SITES):
        saved = BACKUP/f'nginx-site-{i}'
        if path.is_symlink() or path.exists(): path.unlink()
        if saved.is_symlink(): path.symlink_to(os.readlink(saved))
        else: shutil.copy2(saved, path)

def rollback():
    global ACTIVE_SHA
    phase('ROLLBACK')
    for unit in reversed(UNITS): run(['/usr/bin/systemctl', 'stop', unit])
    current = revision()
    if current == '0011_workspace_images':
        gate(STATE['backup'], 'Rollback requires verified backup')
        with ENGINE.connect() as db:
            gate(db.execute(text('SELECT COUNT(*) FROM workspace_image_artifacts')).scalar_one() == 0, 'Artifacts exist; destructive rollback forbidden')
        migrate('down')
    gate(revision() == '0010_document_lifecycle', 'Unexpected schema during rollback; manual preservation required')
    gate(not inspect(ENGINE).has_table('workspace_image_artifacts'), 'Partial migration requires manual preservation; not deleting data')
    restore_runtime_dropins()
    restore_sites()
    nginx_check()
    activate_runtime(ROLLBACK_RUNTIME, ROLLBACK_SHA, '0010_document_lifecycle')
    run(['/usr/bin/systemctl', 'reload', 'nginx'])
    wait_frontend(OLD)
    verify_preserved_backup()
    verify_protected()
    ACTIVE_SHA = ROLLBACK_SHA
    print('ROLLBACK_COMPLETE=' + ROLLBACK_SHA, flush=True)

def verify_protected():
    for path, original in PROTECTED.items(): gate(digest(path) == original, 'Protected configuration changed')
    gate(OPERATIONAL_HEAD is not None and git('rev-parse', 'HEAD') == OPERATIONAL_HEAD, 'Operational HEAD changed during release')
    gate(git('rev-parse', 'origin/trident-ai') == OPERATIONAL_HEAD, 'Operational origin changed during release')
    verify_clean_checkout()
    gate(git('rev-parse', 'refs/heads/main') == initial_main, 'main changed during release')
    gate(git('rev-parse', 'trident-ai-v1.0.0^{commit}') == GOLD, 'Gold changed during release')

def verify_preserved_backup():
    gate(BACKUP != PRESERVED_BACKUP and not BACKUP.is_relative_to(PRESERVED_BACKUP), 'Refusing to replace existing backup')
    gate(PRESERVED_BACKUP.is_dir() and not PRESERVED_BACKUP.is_symlink(), 'Verified recovery backup missing')
    gate((PRESERVED_BACKUP/'BACKUP_VERIFIED').is_file(), 'Recovery backup verification marker missing')
    manifest = json.loads((PRESERVED_BACKUP/'SHA256.json').read_text())
    gate(any(name.startswith('database.') for name in manifest), 'Recovery database backup absent')
    for name, checksum in manifest.items():
        relative = pathlib.PurePosixPath(name)
        gate(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe backup manifest path')
        path = PRESERVED_BACKUP/relative
        gate(path.is_file() and not path.is_symlink() and digest(path) == checksum, 'Recovery backup checksum mismatch')

def report(success):
    print('RELEASE_SHA=' + RELEASE_SHA)
    print('ACTIVE_PRODUCTION_SHA=' + ACTIVE_SHA)
    print('ROLLBACK_SHA=' + ROLLBACK_SHA)
    print('BACKUP=' + ('VERIFIED ' + str(BACKUP) if STATE['backup'] else 'NOT_COMPLETED'))
    print('MIGRATION=' + ('0011_workspace_images PASS' if success else 'NOT_RELEASED'))
    print('FRONTEND=' + ('PASS ' + str(NEW) if success else 'NOT_RELEASED'))
    print('BACKEND=' + ('PASS' if success else 'NOT_RELEASED'))
    print('SMOKE=' + ('PASS public/assets/health/auth-boundaries; authenticated=' + ('PASS' if AUTHENTICATED else 'NOT_VERIFIED') if success else 'FAIL'))
    print('IMAGE_ENGINE=DISABLED; no billable request')
    print('URL=https://' + DOMAIN)
    print('REMAINING=real iPhone visual/fluidity and interactive OIDC acceptance' + ('' if AUTHENTICATED else '; authenticated module flows need a legitimate user session'))
    print('Founder visual validation: PENDING', flush=True)

def run_delivery_self_tests():
    # Kept in the only allowed operational path. No production entrypoint executes.
    import ast
    import contextlib
    import types
    import unittest
    from unittest.mock import patch

    script = (REPO/OPS_SCRIPT_PATH).read_text()
    tree = ast.parse(script.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0])
    main = next(node for node in tree.body if isinstance(node, ast.Try))
    start = next(i for i, node in enumerate(main.body) if ast.unparse(node) == "phase('MIGRATE_0011')")
    finish = next(i for i, node in enumerate(main.body) if ast.unparse(node) == "phase('SWITCH_NGINX')")
    # Exercise the actual activation statements and actual top-level failure handler.
    scenario_code = compile(ast.fix_missing_locations(ast.Module(body=[ast.Try(
        body=main.body[start:finish+1] + [ast.parse("phase('PRODUCTION_SMOKE')").body[0]],
        handlers=main.handlers, orelse=[], finalbody=[])], type_ignores=[])), '<isolated-activation>', 'exec')
    runtime_defs = [node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name in {'activate_runtime', 'wait_backend', 'wait_worker'}]

    class OperationalHeadTests(unittest.TestCase):
        def setUp(self):
            temporary = tempfile.TemporaryDirectory(prefix='trident-ops-git-test-')
            self.addCleanup(temporary.cleanup)
            self.repo = pathlib.Path(temporary.name)
            self.g('init', '--initial-branch=trident-ai', '--template=')
            (self.repo/'app.txt').write_text('immutable candidate fixture\n')
            self.g('add', 'app.txt'); self.g('commit', '-m', 'candidate fixture')
            self.candidate = self.g('rev-parse', 'HEAD')
            (self.repo/'scripts').mkdir()
            (self.repo/OPS_SCRIPT_PATH).write_text('# operational fixture\n')
            self.g('add', OPS_SCRIPT_PATH); self.g('commit', '-m', 'separate operational fixture')
            self.ops = self.g('rev-parse', 'HEAD')
            self.g('update-ref', 'refs/remotes/origin/trident-ai', self.ops)
            self.g('update-ref', 'refs/heads/main', self.candidate)
            self.g('update-ref', 'refs/tags/trident-ai-v1.0.0', self.candidate)
            context = patch.dict(globals(), REPO=self.repo, RELEASE_SHA=self.candidate,
                OPERATIONAL_HEAD=self.ops, initial_main=self.candidate, GOLD=self.candidate, PROTECTED={})
            context.start(); self.addCleanup(context.stop)

        def g(self, *args):
            result = subprocess.run(['/usr/bin/git', '-C', str(self.repo), '-c', 'core.hooksPath=/dev/null',
                '-c', 'commit.gpgSign=false', '-c', 'user.name=Release Fixture',
                '-c', 'user.email=release-fixture@example.invalid', *args],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return result.stdout.decode().strip()

        def test_candidate_plus_separate_operational_commit_accepted(self):
            self.assertNotEqual(self.candidate, self.ops)
            self.assertEqual(capture_operational_head(), self.ops)
            self.assertEqual(RELEASE_SHA, self.candidate)
            verify_protected()

        def test_any_second_committed_path_rejected(self):
            (self.repo/'app.txt').write_text('unapproved change\n')
            self.g('add', 'app.txt'); self.g('commit', '-m', 'forbidden application delta')
            self.g('update-ref', 'refs/remotes/origin/trident-ai', self.g('rev-parse', 'HEAD'))
            with self.assertRaisesRegex(GateError, 'allowlist'): capture_operational_head()

        def test_renamed_path_rejected(self):
            self.g('mv', 'app.txt', 'renamed.txt'); self.g('commit', '-m', 'forbidden rename')
            self.g('update-ref', 'refs/remotes/origin/trident-ai', self.g('rev-parse', 'HEAD'))
            with self.assertRaisesRegex(GateError, 'allowlist'): capture_operational_head()

        def test_local_remote_mismatch_rejected(self):
            self.g('update-ref', 'refs/remotes/origin/trident-ai', self.candidate)
            with self.assertRaisesRegex(GateError, 'not synchronized'): capture_operational_head()

        def test_candidate_must_be_ancestor(self):
            unrelated = self.g('commit-tree', self.g('rev-parse', 'HEAD^{tree}'), '-m', 'unrelated root')
            with patch.dict(globals(), RELEASE_SHA=unrelated):
                with self.assertRaises(GateError): capture_operational_head()

        def test_dirty_worktree_rejected(self):
            (self.repo/OPS_SCRIPT_PATH).write_text('uncommitted operational edit\n')
            with self.assertRaises(GateError): capture_operational_head()

        def test_dirty_index_rejected(self):
            (self.repo/OPS_SCRIPT_PATH).write_text('staged operational edit\n')
            self.g('add', OPS_SCRIPT_PATH)
            with self.assertRaises(GateError): capture_operational_head()

        def test_untracked_source_rejected_visual_review_excluded(self):
            (self.repo/'visual-review').mkdir()
            (self.repo/'visual-review/proof.txt').write_text('fixture\n')
            self.assertEqual(capture_operational_head(), self.ops)
            (self.repo/'unapproved.py').write_text('# fixture\n')
            with self.assertRaisesRegex(GateError, 'untracked'): capture_operational_head()

        def test_operational_head_change_rejected_during_release(self):
            self.g('commit', '--allow-empty', '-m', 'concurrent head movement')
            with self.assertRaisesRegex(GateError, 'Operational HEAD changed'): verify_protected()

        def test_main_and_gold_protection_preserved(self):
            for ref, message in [('refs/heads/main', 'main changed'), ('refs/tags/trident-ai-v1.0.0', 'Gold changed')]:
                with self.subTest(ref=ref):
                    self.g('update-ref', ref, self.ops)
                    with self.assertRaisesRegex(GateError, message): verify_protected()
                    self.g('update-ref', ref, self.candidate)

    class ActivationTests(unittest.TestCase):
        def scenario(self, failure=None):
            events, started = [], set()
            clock, database = [0.0], ['0010_document_lifecycle']
            ns = dict(globals())
            def phase_stub(label):
                ns['STEP'] = label
                events.append(label)
                if label == 'SWITCH_NGINX':
                    self.assertIn('full_runtime_ready', events)
                    self.assertEqual(started, set(UNITS))
                    if failure == 'frontend': raise GateError('fixture frontend failure')
                if label == 'PRODUCTION_SMOKE' and failure == 'smoke': raise GateError('fixture smoke failure')
            def run_stub(args):
                self.assertEqual(args[:2], ['/usr/bin/systemctl', 'start'])
                unit = args[2]; events.append('start:' + unit)
                if unit == UNITS[1]: self.assertIn('backend_ready', events)
                if failure == ('backend_start' if unit == UNITS[0] else 'worker_start'):
                    raise GateError('fixture start failure')
                started.add(unit)
            def identity(root, sha, unit):
                self.assertEqual((root, sha), (NEW, RELEASE_SHA))
                if unit not in started: raise GateError('fixture unit not started')
                if unit == UNITS[1] and failure == 'worker_identity': raise GateError('fixture worker cwd mismatch')
                events.append('identity:' + unit)
                return 100 if unit == UNITS[0] else 200
            def health(suffix):
                if clock[0] < 8 or failure == 'backend_ready': raise GateError('fixture not ready')
                if suffix == 'live': return {'status': 'ok'}
                if suffix == 'ready': return {'status': 'ready'}
                sha = ROLLBACK_SHA if failure == 'backend_recheck' and UNITS[1] in started else RELEASE_SHA
                return dict(build_sha=sha, migration_head='0011_workspace_images',
                    migration_revision='0011_workspace_images', environment='production', security_mode='oidc')
            def migration(direction):
                self.assertEqual(direction, 'up'); events.append('migration')
                if failure == 'migration': raise GateError('fixture migration failure')
                database[0] = '0011_workspace_images'
            def sleep(delay): clock[0] += delay
            ns.update(STATE={'stopped': True, 'success': False}, ENGINE=object(),
                phase=phase_stub, run=run_stub, process_identity=identity, direct_health=health,
                revision=lambda: database[0], migrate=migration, verify_protected=lambda: None,
                write_runtime_dropins=lambda *a: events.append('verified_dropins+daemon_reload'),
                rollback=lambda: events.append('rollback'), report=lambda *a: None,
                time=types.SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
            exec(compile(ast.Module(body=runtime_defs, type_ignores=[]), '<isolated-runtime>', 'exec'), ns)
            actual_wait = ns['wait_backend']
            def wait(*args, **kwargs):
                actual_wait(*args, **kwargs)
                events.append('full_runtime_ready' if kwargs.get('include_worker', True) else 'backend_ready')
            ns['wait_backend'] = wait
            with contextlib.redirect_stdout(io.StringIO()):
                if failure:
                    with self.assertRaises(SystemExit) as raised: exec(scenario_code, ns)
                    self.assertEqual(raised.exception.code, 1)
                    self.assertIn('rollback', events)
                else: exec(scenario_code, ns)
            return events, clock[0]

        def test_backend_ready_before_worker_and_full_runtime_before_frontend(self):
            events, elapsed = self.scenario()
            self.assertGreaterEqual(elapsed, 8)
            self.assertLess(events.index('migration'), events.index('verified_dropins+daemon_reload'))
            self.assertLess(events.index('verified_dropins+daemon_reload'), events.index('start:' + UNITS[0]))
            self.assertLess(events.index('backend_ready'), events.index('start:' + UNITS[1]))
            self.assertLess(events.index('start:' + UNITS[1]), events.index('identity:' + UNITS[1]))
            self.assertLess(events.index('identity:' + UNITS[1]), events.index('full_runtime_ready'))
            self.assertLess(events.index('full_runtime_ready'), events.index('SWITCH_NGINX'))

        def test_backend_failure_never_starts_worker(self):
            for failure in ('backend_start', 'backend_ready'):
                with self.subTest(failure=failure):
                    events, elapsed = self.scenario(failure)
                    self.assertNotIn('start:' + UNITS[1], events)
                    self.assertNotIn('SWITCH_NGINX', events)
                    if failure == 'backend_ready': self.assertEqual(elapsed, READINESS_TIMEOUT)

        def test_worker_failure_rolls_back_before_frontend(self):
            for failure in ('worker_start', 'worker_identity'):
                with self.subTest(failure=failure):
                    events, elapsed = self.scenario(failure)
                    self.assertIn('backend_ready', events)
                    self.assertNotIn('SWITCH_NGINX', events)
                    if failure == 'worker_identity': self.assertEqual(elapsed, 8 + READINESS_TIMEOUT)

        def test_backend_recheck_failure_blocks_frontend(self):
            events, _ = self.scenario('backend_recheck')
            self.assertIn('identity:' + UNITS[1], events)
            self.assertNotIn('SWITCH_NGINX', events)

        def test_failure_handler_covers_migration_frontend_and_smoke(self):
            for failure in ('migration', 'frontend', 'smoke'):
                with self.subTest(failure=failure):
                    events, _ = self.scenario(failure)
                    self.assertEqual(events[-1], 'rollback')
                    if failure == 'migration': self.assertNotIn('start:' + UNITS[0], events)

    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case)
        for case in (OperationalHeadTests, ActivationTests))
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()

if sys.argv[1:] == ['--self-test']:
    sys.exit(0 if run_delivery_self_tests() else 1)

def interrupted(signum, frame): raise GateError('Release interrupted by signal')
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)

try:
    gate(os.geteuid() == 0, 'Root execution required')
    lock = open('/run/lock/trident-spatial-release.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    OPERATIONAL_HEAD = capture_operational_head()
    gate(git('rev-parse', 'trident-ai-v1.0.0^{commit}') == GOLD, 'Gold mismatch')
    initial_main = git('rev-parse', 'refs/heads/main')
    gate(ARCHIVE.is_file() and digest(ARCHIVE) == ARCHIVE_HASH, 'Approved archive checksum mismatch')
    gate((OLD/'frontend/dist/index.html').is_file(), 'Rollback release missing')
    config = nginx_check()
    gate(all(p.is_file() and p.resolve() in [s.absolute() for s in SITES] for p in SITES), 'Unexpected production vhost topology')
    if f'root {NEW}/frontend/dist;' in config:
        verify_source(NEW, RELEASE_SHA); verify_frontend(NEW)
        wait_backend(NEW, RELEASE_SHA, '0011_workspace_images')
        gate(http('/')[0] == (NEW/'frontend/dist/index.html').read_bytes(), 'Existing target homepage differs')
        print('ALREADY_ACTIVE=' + RELEASE_SHA)
        print('Founder visual validation: PENDING'); sys.exit(0)
    gate(f'root {OLD}/frontend/dist;' in config, 'Unexpected active rollback SHA')
    gate(http('/')[0] == (OLD/'frontend/dist/index.html').read_bytes(), 'Active homepage is not rollback release')
    ACTIVE_SHA = ROLLBACK_SHA
    json_http('/api/health/ready')
    build = json_http('/api/health/build')
    gate(build['build_sha'] == ROLLBACK_SHA and build['migration_head'] == '0010_document_lifecycle' and build['migration_revision'] == '0010_document_lifecycle', 'Unexpected rollback build/migration identity')
    running_sha = build['build_sha']
    gate(re.fullmatch('[0-9a-f]{40}', running_sha) is not None, 'Cannot establish running backend revision')
    for tree in ('app', 'requirements.txt'):
        gate(git('rev-parse', f'{running_sha}:{tree}') == git('rev-parse', f'{ROLLBACK_SHA}:{tree}'), 'Running backend is not rollback-compatible')
    for unit in UNITS:
        gate(unit_property(unit, 'User') == 'administrator', 'Unexpected service identity')
        process_identity(ROLLBACK_RUNTIME, ROLLBACK_SHA, unit)
        gate(str(pathlib.Path('/etc/systemd/system')/(unit+'.d')/DROPIN) in unit_property(unit, 'DropInPaths').split(), 'Recovered rollback override missing')
        gate('EnvironmentFile=/etc/trident/trident-ai.env' in run(['/usr/bin/systemctl', 'cat', unit]).decode(), 'Unexpected service environment source')
    pid = int(unit_property(UNITS[0], 'MainPID')); gate(pid > 1, 'Backend not running')
    boot = next(int(line.split()[1]) for line in pathlib.Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
    started = boot + int(pathlib.Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]) / os.sysconf('SC_CLK_TCK')
    gate(ENV_FILE.stat().st_mtime <= started + 3, 'Production environment changed since backend start; runtime reconciliation required')
    RUNTIME_ENV = service_env(pid)
    CFG = configuration(RUNTIME_ENV, ROLLBACK_RUNTIME)
    gate(CFG['environment'] == 'production' and CFG['security'] == 'oidc', 'Unsafe runtime configuration')
    gate(CFG['redirect'] == 'https://trident-ai.org/api/v1/session/callback', 'Production callback mismatch')
    gate(CFG['logout'] == 'https://trident-ai.org/', 'Production logout mismatch')
    worker_cfg = configuration(service_env(int(unit_property(UNITS[1], 'MainPID'))), ROLLBACK_RUNTIME)
    gate(all(CFG[k] == worker_cfg[k] for k in ('database', 'documents', 'vectors')), 'Backend/worker data mismatch')
    gate(make_url(CFG['database']).get_backend_name() in ('postgresql', 'sqlite'), 'Unsupported database engine')
    for key in ('documents', 'vectors', 'images'):
        p = pathlib.Path(CFG[key]); gate(p.is_absolute() and p != pathlib.Path('/') and not p.is_relative_to(ROOT), 'Unsafe runtime data directory')
    gate(pathlib.Path(CFG['documents']).is_dir() and pathlib.Path(CFG['vectors']).is_dir(), 'Runtime data directory missing')
    # Relative database locations would change under an immutable working directory.
    database_url = make_url(CFG['database'])
    if database_url.get_backend_name() == 'sqlite':
        gate(pathlib.Path(database_url.database).is_absolute(), 'Relative SQLite URL: explicit runtime review required')
    else:
        gate(database_url.host in (None, '', 'localhost', '127.0.0.1', '::1') or database_url.host.startswith('/var/run/postgresql'), 'Remote database not authorized')
    ENGINE = create_engine(CFG['database'], pool_pre_ping=True)
    gate(revision() == '0010_document_lifecycle' and not inspect(ENGINE).has_table('workspace_image_artifacts'), 'Migration baseline differs')
    wait_backend(ROLLBACK_RUNTIME, ROLLBACK_SHA, '0010_document_lifecycle')
    verify_preserved_backup()
    verify_runtime_dropins(render_runtime_dropins(NEW, RELEASE_SHA))
    verify_runtime_dropins(render_runtime_dropins(ROLLBACK_RUNTIME, ROLLBACK_SHA))
    gate(shutil.disk_usage(ROOT).free > 12 * 1024**3 and shutil.disk_usage(BACKUP.parent.parent).free > 12 * 1024**3, 'Insufficient safe staging/backup space')
    PROTECTED[ENV_FILE] = digest(ENV_FILE)
    for unit in UNITS:
        fragment = pathlib.Path(unit_property(unit, 'FragmentPath')); PROTECTED[fragment] = digest(fragment)
    # Optional legitimate user cookie; never mint/borrow a session or impersonate an account.
    cookie_file = pathlib.Path('/run/trident-release-session.cookie')
    if cookie_file.exists():
        st = cookie_file.stat()
        gate(not cookie_file.is_symlink() and st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o600, 'Unsafe optional smoke-cookie file permissions')
        token = cookie_file.read_text().strip()
        gate(re.fullmatch('[A-Za-z0-9_-]{32,256}', token) is not None, 'Invalid smoke cookie format')
        COOKIE = 'trident_session=' + token
        json_http('/api/v1/session', cookie=COOKIE)

    phase('BACKUP_CONFIG_AND_ROLLBACK_RUNTIME')
    BACKUP.mkdir(parents=True, mode=0o700); BACKUP.chmod(0o700)
    shutil.copy2(ENV_FILE, BACKUP/'production-environment.backup')
    for i, path in enumerate(SITES): shutil.copy2(path, BACKUP/f'nginx-site-{i}', follow_symlinks=False)
    for unit in UNITS:
        (BACKUP/(unit+'.effective')).write_bytes(run(['/usr/bin/systemctl', 'cat', unit]))
        fragment = pathlib.Path(unit_property(unit, 'FragmentPath')); shutil.copy2(fragment, BACKUP/unit)
        dropins = pathlib.Path('/etc/systemd/system')/(unit+'.d')
        if dropins.exists(): shutil.copytree(dropins, BACKUP/(unit+'.d'), symlinks=True)
    nginx_check(save=True)
    # Reuse the verified immutable recovery runtime without writing to it.
    # Fresh attempt backups are additive, outside the preserved recovery backup.
    verify_source(ROLLBACK_RUNTIME, ROLLBACK_SHA)
    gate(configuration(runtime_env(ROLLBACK_SHA), ROLLBACK_RUNTIME) == CFG, 'Rollback runtime settings differ from current production')
    gate(run([ROLLBACK_RUNTIME/'venv/bin/python', '-c', 'from app.database.schema import HEAD_REVISION; print(HEAD_REVISION)'], cwd=ROLLBACK_RUNTIME, env=runtime_env(ROLLBACK_SHA), user=True).strip() == b'0010_document_lifecycle', 'Rollback runtime cannot load')
    archive_directory(ROLLBACK_RUNTIME, BACKUP/'rollback-runtime.tar.gz')

    phase('STAGE_EXACT_APPROVED_RELEASE')
    if NEW.exists():
        verify_source(NEW, RELEASE_SHA); ASSETS = verify_frontend(NEW)
        gate((NEW/'venv/bin/python').is_file(), 'Incomplete existing target runtime; refusing overwrite')
        CANDIDATE = NEW
    else:
        staging = ROOT/f'.{RELEASE_SHA}.staging-{STAMP}'
        staging.mkdir(mode=0o700)
        extract_checked(ARCHIVE, staging)
        gate((staging/'RELEASE_SHA').read_text().strip() == RELEASE_SHA and (staging/'ROLLBACK_SHA').read_text().strip() == ROLLBACK_SHA, 'Archive SHA marker mismatch')
        verify_source(staging, RELEASE_SHA); ASSETS = verify_frontend(staging)
        # Clone the known runtime, install pinned requirements only into the clone.
        shutil.copytree(ROLLBACK_RUNTIME/'venv', staging/'venv', symlinks=True)
        for base, dirs, files in os.walk(staging):
            os.chown(base, SERVICE_USER.pw_uid, SERVICE_USER.pw_gid)
            for name in files:
                path = pathlib.Path(base)/name
                if not path.is_symlink(): os.chown(path, SERVICE_USER.pw_uid, SERVICE_USER.pw_gid)
        gate(run([staging/'venv/bin/python', '-c', 'import sys; print(sys.prefix)'], user=True).decode().strip() == str(staging/'venv'), 'Cloned Python environment resolves outside staging')
        run([staging/'venv/bin/python', '-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', '-r', staging/'requirements.txt'], cwd=staging, user=True, timeout=1800)
        run([staging/'venv/bin/python', '-m', 'pip', 'check'], cwd=staging, user=True)
        verify_source(staging, RELEASE_SHA); verify_frontend(staging)
        frozen_tree(staging); CANDIDATE = staging
    gate(ASSETS, 'No entry assets')
    gate(configuration(runtime_env(RELEASE_SHA), CANDIDATE) == CFG, 'Candidate runtime settings differ from current production')
    gate(run([CANDIDATE/'venv/bin/python', '-c', 'from app.database.schema import HEAD_REVISION; import PIL; print(HEAD_REVISION)'], cwd=CANDIDATE, env=runtime_env(RELEASE_SHA), user=True).strip() == b'0011_workspace_images', 'Candidate runtime cannot load')
    run(['/usr/sbin/runuser', '-u', 'www-data', '--', '/usr/bin/test', '-r', CANDIDATE/'frontend/dist/index.html'])

    phase('QUIESCE_AND_VERIFY_DATABASE_DATA_BACKUP')
    STATE['stopped'] = True
    for unit in reversed(UNITS): run(['/usr/bin/systemctl', 'stop', unit])
    backup_database()
    data_paths = []
    for key in ('documents', 'vectors', 'images'):
        p = pathlib.Path(CFG[key])
        if p.exists() and not any(p == prior or p.is_relative_to(prior) for prior in data_paths):
            archive_directory(p, BACKUP/f'{key}.tar.gz'); data_paths.append(p)
    manifest = {str(p.relative_to(BACKUP)): digest(p) for p in BACKUP.rglob('*') if p.is_file() and not p.is_symlink()}
    gate(manifest and any(name.startswith('database.') for name in manifest), 'Database backup absent')
    (BACKUP/'SHA256.json').write_text(json.dumps(manifest, sort_keys=True, indent=2))
    for name, value in manifest.items(): gate(digest(BACKUP/name) == value, 'Backup checksum verification failed')
    STATE['backup'] = True
    (BACKUP/'BACKUP_VERIFIED').write_text(STAMP+'\n')

    phase('INSTALL_IMMUTABLE_RELEASE')
    if CANDIDATE != NEW: CANDIDATE.rename(NEW)
    gate(run([NEW/'venv/bin/python', '-c', 'import sys; print(sys.prefix)'], user=True).decode().strip() == str(NEW/'venv'), 'Installed Python environment resolves outside immutable release')

    phase('MIGRATE_0011')
    verify_protected(); gate(revision() == '0010_document_lifecycle', 'Schema changed before migration')
    STATE['migration'] = True
    migrate('up')
    gate(revision() == '0011_workspace_images', 'Migration not finalized')
    phase('ACTIVATE_MATCHING_BACKEND')
    service_since = dt.datetime.now(dt.timezone.utc).isoformat()
    write_runtime_dropins(NEW, RELEASE_SHA)
    activate_runtime(NEW, RELEASE_SHA, '0011_workspace_images')
    phase('SWITCH_NGINX')
    smoke_since = dt.datetime.now(dt.timezone.utc).isoformat()
    access = pathlib.Path('/var/log/nginx/access.log')
    LOG_OFFSET = (access.stat().st_ino, access.stat().st_size)
    nginx_errors = pathlib.Path('/var/log/nginx/error.log')
    error_offset = (nginx_errors.stat().st_ino, nginx_errors.stat().st_size)
    STATE['nginx'] = True
    for path in dict.fromkeys(p.resolve() for p in SITES):
        original = path.read_text()
        needle = f'root {OLD}/frontend/dist;'
        gate(original.count(needle) == 1, 'Unexpected root directive during switch')
        updated = original.replace(needle, f'root {NEW}/frontend/dist;')
        # Authenticated image previews use local blob URLs; no provider domain is added.
        updated = updated.replace("img-src 'self' data:;", "img-src 'self' data: blob:;")
        gate("img-src 'self' data: blob:;" in updated, 'Unreviewed image CSP; refusing policy rewrite')
        path.write_text(updated)
    nginx_check(); run(['/usr/bin/systemctl', 'reload', 'nginx'])
    STATE['switched'] = True
    wait_frontend(NEW)
    ACTIVE_SHA = RELEASE_SHA

    phase('PRODUCTION_SMOKE')
    public_index = http('/', public=True)[0].decode()
    gate(all(asset in public_index for asset in ASSETS), 'Public homepage is not the approved build')
    for asset in ASSETS: http(asset, public=True)
    for suffix in ('live', 'ready', 'build'): json_http('/api/health/'+suffix, public=True)
    wait_backend(NEW, RELEASE_SHA, '0011_workspace_images')
    for module in ('WorkspaceHome', 'ConversationsView', 'DocumentsView', 'MemoryView', 'FilesView', 'ActivityView', 'SettingsView', 'ArtifactsView', 'ImageCard', 'ConsentPage'):
        files = list((NEW/'frontend/dist/assets').glob(module+'-*.js'))
        gate(len(files) == 1, 'Required module bundle missing: '+module)
        gate(http('/assets/'+files[0].name)[0] == files[0].read_bytes(), 'Module bundle mismatch: '+module)
    gate(json_http('/api/v1/session/configuration')['data']['enabled'] is True, 'Interactive auth disabled')
    http('/api/v1/session', 401)
    http('/api/v1/session/callback', 401)
    http('/api/openapi.json', 404)
    http('/oauth/consent')
    login = json_http('/api/v1/session/login', expected=201, method='POST', payload={'return_to':'/'})
    authorize = urllib.parse.urlparse(login['data']['authorization_url'])
    query = urllib.parse.parse_qs(authorize.query)
    gate(authorize.scheme == 'https' and authorize.hostname == urllib.parse.urlparse(CFG['issuer']).hostname, 'Unexpected OIDC provider')
    gate(query.get('client_id') == [CFG['client']] and query.get('redirect_uri') == [CFG['redirect']], 'OIDC client/callback changed')
    gate(query.get('response_type') == ['code'] and query.get('code_challenge_method') == ['S256'] and bool(query.get('code_challenge')), 'PKCE missing')
    prefix = '/api/v1/workspaces/00000000-0000-4000-8000-000000000001'
    paths = ['', '/overview', '/conversations', '/documents', '/memories', '/activity', '/images', '/images/capability']
    http('/api/v1/workspaces', 401)
    for suffix in paths: http(prefix+suffix, 401)
    if COOKIE:
        session = json_http('/api/v1/session', cookie=COOKIE)['data']
        workspaces = json_http('/api/v1/workspaces', cookie=COOKIE)['data']
        gate(bool(workspaces), 'Authenticated smoke account has no Workspace')
        workspace_id = session.get('active_workspace_id') or workspaces[0]['id']
        gate(re.fullmatch('[0-9a-fA-F-]{36}', workspace_id) is not None, 'Unexpected authorized Workspace ID')
        for suffix in paths: json_http('/api/v1/workspaces/'+workspace_id+suffix, cookie=COOKIE)
        capability = json_http('/api/v1/workspaces/'+workspace_id+'/images/capability', cookie=COOKIE)['data']
        gate(capability['available'] is False, 'Image provider unexpectedly enabled')
        AUTHENTICATED = True
    backend_pid = int(unit_property(UNITS[0], 'MainPID'))
    gate(service_env(backend_pid).get('TRIDENT_IMAGE_PROVIDER') == 'disabled', 'Image engine activation forbidden in this release')
    # Verify schema API boundary without an authenticated create/provider request.
    with ENGINE.connect() as db: gate(db.execute(text('SELECT COUNT(*) FROM workspace_image_artifacts')).scalar_one() == 0, 'Unexpected image task during disabled release gate')
    nginx_check(); verify_protected()
    gate(access.stat().st_ino == LOG_OFFSET[0] and access.stat().st_size >= LOG_OFFSET[1], 'Access log rotated; cannot verify smoke window')
    with access.open('rb') as f: f.seek(LOG_OFFSET[1]); lines = f.read().decode(errors='replace').splitlines()
    failed = [line for line in lines if 'trident_release_probe='+STAMP in line and re.search(r'"\s+5\d\d\s', line)]
    gate(not failed, 'Nginx recorded 5xx for release smoke requests')
    gate(nginx_errors.stat().st_ino == error_offset[0] and nginx_errors.stat().st_size >= error_offset[1], 'Nginx error log rotated during smoke gate')
    with nginx_errors.open('rb') as f: f.seek(error_offset[1]); error_lines = f.read().decode(errors='replace').splitlines()
    gate(not any(DOMAIN in line and re.search(r'\[(?:error|crit|alert|emerg)\]', line) for line in error_lines), 'Nginx production error during smoke window')
    journals = run(['/usr/bin/journalctl', '-u', UNITS[0], '-u', UNITS[1], '--since', service_since, '--no-pager', '-o', 'json'])
    (BACKUP/'post-smoke-journal.jsonl').write_bytes(journals)
    for line in journals.splitlines():
        entry = json.loads(line)
        message = entry.get('MESSAGE', '')
        gate(not re.search(r'Traceback \(most recent call last\)|\bCRITICAL\b|\bERROR\b|"level"\s*:\s*"error"', message), 'Critical backend/worker log after smoke')
    (BACKUP/'RELEASE_SUCCESS').write_text(RELEASE_SHA+'\n')
    STATE['success'] = True
    report(True)
except (Exception, KeyboardInterrupt) as error:
    reason = str(error) if isinstance(error, GateError) else type(error).__name__
    print('FAILED_CHECK='+STEP, flush=True)
    print('FAILURE='+reason, flush=True)
    if STATE['stopped'] and not STATE['success']:
        try: rollback()
        except BaseException:
            print('ROLLBACK_INCOMPLETE=manual preservation required; no destructive database restore attempted', flush=True)
            print('BACKUP_PATH='+str(BACKUP), flush=True)
            print('Founder visual validation: PENDING', flush=True)
            sys.exit(2)
    report(False)
    sys.exit(1)
PY
