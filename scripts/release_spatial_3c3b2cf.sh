#!/usr/bin/bash
# Approved release only. No source edits, secret provisioning or paid image calls.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
umask 077
[[ $EUID -eq 0 ]] || { printf 'ERROR: local root execution required.\n' >&2; exit 1; }
exec /home/administrator/ai-rag-chatbot/venv/bin/python - <<'PY'
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
    return run(['/usr/bin/git', '-c', f'safe.directory={REPO}', '-C', REPO, *args]).decode().strip()

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

def wait_backend(root, sha, schema):
    gate(READINESS_TIMEOUT >= 30, 'Unsafe readiness timeout')
    deadline = time.monotonic() + READINESS_TIMEOUT
    last_failure = 'not checked'
    while True:
        try:
            pids = {unit: process_identity(root, sha, unit) for unit in UNITS}
            live = direct_health('live')
            ready = direct_health('ready')
            build = direct_health('build')
            gate(live['status'] == 'ok' and ready['status'] == 'ready', 'Backend not ready')
            gate(build['build_sha'] == sha and build['migration_revision'] == schema and build['migration_head'] == schema, 'Backend SHA/schema mismatch')
            gate(build['environment'] == 'production' and build['security_mode'] == 'oidc', 'Production security mode changed')
            if ENGINE is not None: gate(revision() == schema, 'Database revision differs from health identity')
            for unit in UNITS:
                gate(process_identity(root, sha, unit) == pids[unit], 'Runtime restarted during health checks')
            return
        except (GateError, OSError, ValueError, KeyError, http_client.HTTPException) as error:
            last_failure = str(error) if isinstance(error, GateError) else type(error).__name__
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise GateError(f'Backend readiness/identity timeout ({READINESS_TIMEOUT}s): {last_failure}')
        time.sleep(min(2, remaining))

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
    for unit in UNITS: run(['/usr/bin/systemctl', 'start', unit])
    wait_backend(ROLLBACK_RUNTIME, ROLLBACK_SHA, '0010_document_lifecycle')
    run(['/usr/bin/systemctl', 'reload', 'nginx'])
    wait_frontend(OLD)
    verify_preserved_backup()
    verify_protected()
    ACTIVE_SHA = ROLLBACK_SHA
    print('ROLLBACK_COMPLETE=' + ROLLBACK_SHA, flush=True)

def verify_protected():
    for path, original in PROTECTED.items(): gate(digest(path) == original, 'Protected configuration changed')
    gate(git('rev-parse', 'HEAD') == RELEASE_SHA, 'Checkout changed during release')
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

def interrupted(signum, frame): raise GateError('Release interrupted by signal')
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)

try:
    gate(os.geteuid() == 0, 'Root execution required')
    lock = open('/run/lock/trident-spatial-release.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    gate(git('branch', '--show-current') == 'trident-ai', 'Wrong branch')
    gate(git('rev-parse', 'HEAD') == RELEASE_SHA and git('rev-parse', 'origin/trident-ai') == RELEASE_SHA, 'Candidate SHA mismatch')
    gate(git('rev-parse', 'trident-ai-v1.0.0^{commit}') == GOLD, 'Gold mismatch')
    initial_main = git('rev-parse', 'refs/heads/main')
    git('diff', '--exit-code'); git('diff', '--cached', '--exit-code'); git('diff', '--check')
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
    for unit in UNITS: run(['/usr/bin/systemctl', 'start', unit])
    wait_backend(NEW, RELEASE_SHA, '0011_workspace_images')
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
