#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/.openclaw/workspace/cheesebot-status
python3 status_snapshot.py
if ! git diff --quiet -- status.json; then
  git add status.json
  git commit -m "Update status snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push origin main
fi
