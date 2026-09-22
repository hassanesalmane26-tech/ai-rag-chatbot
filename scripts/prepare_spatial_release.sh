#!/usr/bin/env bash
# Preparation only. No sudo, production writes, migration or service restart.
set -euo pipefail
umask 077
REPO=/home/administrator/ai-rag-chatbot
ROLLBACK_SHA=4223cc2a4e7629283b1310e14a412db419baec6b
cd "$REPO"
[[ $(git branch --show-current) == trident-ai ]]
SHA=$(git rev-parse HEAD)
[[ "$SHA" == "$(git rev-parse origin/trident-ai)" ]]
git diff --quiet
git diff --cached --quiet
git diff --check
[[ -f "$REPO/frontend/.env.production" ]]
[[ -f "/var/www/trident-ai/releases/$ROLLBACK_SHA/frontend/dist/index.html" ]]
STAGE=$(mktemp -d "/tmp/trident-spatial-release-${SHA:0:12}.XXXXXX")
mkdir -m 0700 "$STAGE/source"
git archive "$SHA" | tar -x -C "$STAGE/source"
# Never copy untracked preview/config files. Build from the locked dependency tree.
npm ci --prefix "$STAGE/source/frontend" --ignore-scripts --no-audit --no-fund
TRIDENT_BUILD_SOURCE="$STAGE/source" TRIDENT_BUILD_REPO="$REPO" node --input-type=module <<'NODE'
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { readFileSync, readdirSync } from 'node:fs';
const source = process.env.TRIDENT_BUILD_SOURCE;
const repo = process.env.TRIDENT_BUILD_REPO;
// Old tmux/preview VITE values must never override the approved production file.
for (const name of Object.keys(process.env)) if (name.startsWith('VITE_')) delete process.env[name];
const { loadEnv } = await import(pathToFileURL(`${source}/frontend/node_modules/vite/dist/node/index.js`));
const values = loadEnv('production', `${repo}/frontend`, 'VITE_');
const allowed = new Set(['VITE_API_BASE_URL', 'VITE_SUPABASE_PROJECT_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY']);
if (Object.keys(values).some(name => !allowed.has(name))) throw new Error('Unexpected frontend production variable: manual review required');
if (values.VITE_API_BASE_URL && values.VITE_API_BASE_URL !== '/api') throw new Error('Production API must be same-origin /api');
if (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(values.VITE_SUPABASE_PROJECT_URL || '')) throw new Error('Invalid production Supabase origin');
const key = values.VITE_SUPABASE_PUBLISHABLE_KEY || '';
let publicKey = /^sb_publishable_[A-Za-z0-9_-]+$/.test(key);
if (!publicKey) {
  try { publicKey = JSON.parse(Buffer.from(key.split('.')[1], 'base64url')).role === 'anon'; } catch { /* reject */ }
}
if (!publicKey) throw new Error('Only a Supabase publishable/anon key can enter the frontend');
const result = spawnSync('npm', ['run', 'build'], {cwd:`${source}/frontend`, stdio:'inherit', env:{...process.env, ...values, VITE_API_BASE_URL:'/api'}});
if (result.status !== 0) process.exit(result.status || 1);
// Prefix order matters after CSS minification: a prefixed-only override leaves
// legacy unprefixed blur active in browsers which ignore the prefixed alias.
const assets = `${source}/frontend/dist/assets`;
const css = readdirSync(assets).filter(name => name.endsWith('.css')).map(name => readFileSync(`${assets}/${name}`, 'utf8')).join('\n');
const rules = [...css.matchAll(/[^{}]*settings-card[^{}]*\{([^{}]*)\}/g)];
if (!rules.some(rule => rule[0].includes('.main-layout :is(') && /(?:^|;)backdrop-filter:none(?:;|$)/.test(rule[1]))) {
  throw new Error('Compiled mobile Settings blur protection is missing');
}
NODE
[[ -s "$STAGE/source/frontend/dist/index.html" ]]
"$REPO/venv/bin/python" -m app.operations.artifacts "$STAGE/source/frontend/dist" > "$STAGE/source/FRONTEND_MANIFEST.json"
printf '%s\n' "$SHA" > "$STAGE/source/RELEASE_SHA"
printf '%s\n' "$ROLLBACK_SHA" > "$STAGE/source/ROLLBACK_SHA"
git diff --name-only "$ROLLBACK_SHA" "$SHA" > "$STAGE/source/CHANGED_FILES.txt"
tar --exclude='./frontend/node_modules' -czf "$STAGE/release.tar.gz" -C "$STAGE/source" .
sha256sum "$STAGE/release.tar.gz" > "$STAGE/release.tar.gz.sha256"
chmod 0400 "$STAGE/release.tar.gz" "$STAGE/release.tar.gz.sha256"
printf 'PREPARED_SHA=%s\nSTAGING_DIRECTORY=%s\nPLANNED_RELEASE=/var/www/trident-ai/releases/%s\nROLLBACK_SHA=%s\nDEPLOYED=no\n' "$SHA" "$STAGE" "$SHA" "$ROLLBACK_SHA"
