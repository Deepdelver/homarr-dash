#!/usr/bin/env bash
#
# backup-homarr-config.sh — periodic exporter for the live Homarr dashboard config.
#
# 1. Copies /appdata/db/db.sqlite out of the running Homarr pod (k3s).
# 2. Runs scripts/export-homarr-config.py -> safe JSON under config/ (no secrets).
# 3. Commits + pushes to origin/main IF there are changes.
#
# Intended to be run by cron (see README "Periodic backup" section).
# Requires: kubectl (kubeconfig with homarr namespace access), sqlite3, git.
set -euo pipefail

# Pin runtime deps so this runs unattended under cron (no inherited env/agent).
export KUBECONFIG="${KUBECONFIG:-/home/frank/.kube/config}"
export GIT_SSH_COMMAND="ssh -i /home/frank/.ssh/homarr-dash-deploy -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="homarr"
POD="$(kubectl -n "$NAMESPACE" get pods -l app=homarr -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
CONFIG_DIR="$REPO_ROOT/config"
TMP_DB="$(mktemp /tmp/homarr-db.XXXXXX.sqlite)"
trap 'rm -f "$TMP_DB"' EXIT

if [ -z "$POD" ]; then
  echo "ERROR: no Homarr pod found in namespace $NAMESPACE" >&2
  exit 1
fi

echo "[backup] pod=$POD"
echo "[backup] copying db.sqlite from pod..."
kubectl -n "$NAMESPACE" cp "$POD:/appdata/db/db.sqlite" "$TMP_DB"

echo "[backup] exporting safe config -> $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"
python3 "$REPO_ROOT/scripts/export-homarr-config.py" "$TMP_DB" "$CONFIG_DIR"

# Only commit if something actually changed (avoids commit-noise on every tick).
cd "$REPO_ROOT"
if git diff --quiet "$CONFIG_DIR" && git diff --cached --quiet "$CONFIG_DIR" && \
   [ -z "$(git status --porcelain "$CONFIG_DIR")" ]; then
  echo "[backup] no config changes since last commit — nothing to push."
  exit 0
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "[backup] changes detected on $BRANCH — committing..."
git add "$CONFIG_DIR"
git commit -m "chore(homarr): automated dashboard config backup ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
git push origin "$BRANCH"
echo "[backup] pushed."
