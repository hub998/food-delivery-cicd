#!/usr/bin/env bash
# Runs ON the EC2 server (as root), from inside the unzipped build.
# Installs the new release, switches to it, health-checks it, and rolls back if it is not healthy.
set -euo pipefail

APP=/opt/foodapp
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$SRC/VERSION")"
BUILD="$(cat "$SRC/BUILD" 2>/dev/null || echo manual)"
REL="$APP/releases/${VERSION}-${BUILD}"

echo ">> Deploying version $VERSION (build $BUILD)"
id foodapp >/dev/null 2>&1 || useradd --system --no-create-home --shell /sbin/nologin foodapp
mkdir -p "$APP/releases"

# One shared virtual environment for all releases
[ -d "$APP/venv" ] || python3 -m venv "$APP/venv"

# Copy the new release next to the old ones
rm -rf "$REL"
mkdir -p "$REL"
cp -r "$SRC"/. "$REL"/
"$APP/venv/bin/pip" install --quiet --disable-pip-version-check -r "$REL/requirements.txt"

# systemd service (created once, safe to rewrite)
cat > /etc/systemd/system/foodapp.service <<UNIT
[Unit]
Description=Food Delivery web app
After=network.target

[Service]
User=foodapp
WorkingDirectory=$APP/current
ExecStart=$APP/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:80 app:app
AmbientCapabilities=CAP_NET_BIND_SERVICE
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable foodapp >/dev/null 2>&1 || true

# Switch the "current" link to the new release and restart
PREVIOUS="$(readlink -f "$APP/current" 2>/dev/null || true)"
ln -sfn "$REL" "$APP/current"
systemctl restart foodapp

# Health check: the new version must answer
ok=0
for i in $(seq 1 20); do
  if curl -fsS http://127.0.0.1/health 2>/dev/null | grep -q "\"version\":\"$VERSION\""; then ok=1; break; fi
  sleep 1
done

if [ "$ok" -ne 1 ]; then
  echo "!! New release is NOT healthy"
  if [ -n "$PREVIOUS" ] && [ -d "$PREVIOUS" ]; then
    echo "!! Rolling back to $PREVIOUS"
    ln -sfn "$PREVIOUS" "$APP/current"
    systemctl restart foodapp
  fi
  exit 1
fi

# Keep only the 3 newest releases
ls -1dt "$APP"/releases/* | tail -n +4 | xargs -r rm -rf
echo ">> Deployed OK: version $VERSION is live"
