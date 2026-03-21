#!/usr/bin/env bash
set -euo pipefail
cd /home/ubuntu/.openclaw/workspace/cheesebot-status
python3 status_snapshot.py
python3 injury_status_snapshot.py
python3 nba_games_snapshot.py
python3 stock_snapshot.py
python3 weather_snapshot.py
python3 email_guardrail_snapshot.py
python3 self_audit_snapshot.py
if ! git diff --quiet -- status.json injury-report/data nba-daily-games/data stocks/data weather-reports/data email-guardrail/data self-audit/data; then
  git add status.json injury-report/data nba-daily-games/data stocks/data weather-reports/data email-guardrail/data self-audit/data
  git commit -m "Update status snapshots $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push origin main
fi
