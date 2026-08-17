#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run through the owner-authorized sudo path." >&2
  exit 1
fi
if [[ $# -ne 2 ]]; then
  echo "Usage: $0 SOURCE_CHECKOUT IMMUTABLE_RELEASE_ROOT" >&2
  exit 2
fi

source_checkout=$(readlink -f "$1")
release_root="$2"
case "$release_root" in
  /var/www/trident-ai/releases/*) ;;
  *) echo "Release root must be below /var/www/trident-ai/releases/." >&2; exit 2 ;;
esac
site=/etc/nginx/sites-available/trident-ai
enabled=/etc/nginx/sites-enabled/trident-ai
backup_root=/etc/nginx/trident-ai-backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)

test -f "$source_checkout/frontend/dist/index.html"
test -f "$source_checkout/deploy/nginx/trident-ai-http-bootstrap.conf.template"
test -f "$source_checkout/deploy/nginx/trident-ai.conf.template"
command -v nginx >/dev/null
command -v certbot >/dev/null

install -d -m 0750 "$backup_root/$stamp"
for current in /etc/nginx/sites-available/ai-rag "$site"; do
  if [[ -e "$current" ]]; then
    cp -a "$current" "$backup_root/$stamp/"
  fi
done
if [[ -L "$enabled" ]]; then
  readlink "$enabled" > "$backup_root/$stamp/enabled-link.txt"
fi

install -d -m 0755 "$release_root/frontend"
if [[ -e "$release_root/frontend/dist" ]]; then
  echo "Immutable frontend destination already exists: $release_root/frontend/dist" >&2
  exit 1
fi
staging=$(mktemp -d "$release_root/frontend/.dist.XXXXXX")
cp -a "$source_checkout/frontend/dist/." "$staging/"
find "$staging" -type d -exec chmod 0755 {} +
find "$staging" -type f -exec chmod 0644 {} +
mv "$staging" "$release_root/frontend/dist"

install -d -m 0755 /var/www/letsencrypt
install -m 0644 \
  "$source_checkout/deploy/nginx/trident-ai-http-bootstrap.conf.template" "$site"
ln -sfn "$site" "$enabled"
nginx -t
systemctl reload nginx

certbot certonly --webroot -w /var/www/letsencrypt \
  -d trident-ai.org -d www.trident-ai.org
certbot renew --dry-run

sed "s|__RELEASE_ROOT__|$release_root|g" \
  "$source_checkout/deploy/nginx/trident-ai.conf.template" > "$site.new"
install -m 0644 "$site.new" "$site"
rm -f "$site.new"
nginx -t
systemctl reload nginx

curl --fail --silent --show-error --resolve trident-ai.org:443:127.0.0.1 \
  https://trident-ai.org/ >/dev/null
curl --fail --silent --show-error --resolve trident-ai.org:443:127.0.0.1 \
  https://trident-ai.org/api/health/live >/dev/null
redirect=$(curl --silent --show-error --output /dev/null --write-out '%{redirect_url}' \
  --resolve www.trident-ai.org:443:127.0.0.1 https://www.trident-ai.org/)
test "$redirect" = "https://trident-ai.org/"

echo "Origin TLS and canonical routing validated. Backup: $backup_root/$stamp"
echo "Cloudflare Full (strict) and external HTTPS must still be verified by the owner."
