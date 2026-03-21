#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'email-guardrail' / 'data' / 'overview.json'
STATE_PATH = ROOT.parent / 'memory' / 'email-state.json'
JOB_ID = '3fee9884-7211-4630-b49c-d8c9b8129b87'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_json(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout).strip()
    try:
        return json.loads(p.stdout), None
    except Exception as e:
        return None, f'json parse error: {e}'


def summarize_email_state(state):
    if not isinstance(state, dict):
        return {}
    msgs = state.get('messages') or {}
    threads = state.get('threads') or {}
    msg_vals = list(msgs.values()) if isinstance(msgs, dict) else []
    return {
        'messagesTracked': len(msg_vals),
        'threadsTracked': len(threads) if isinstance(threads, dict) else 0,
        'seenCount': sum(1 for v in msg_vals if isinstance(v, dict) and v.get('seenAt')),
        'actedCount': sum(1 for v in msg_vals if isinstance(v, dict) and v.get('actedAt')),
        'repliedCount': sum(1 for v in msg_vals if isinstance(v, dict) and v.get('repliedAt')),
        'lastCheckedHistoryId': state.get('lastHistoryId') or state.get('last_history_id'),
    }


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    jobs_data, jobs_err = run_json(['openclaw', 'cron', 'list', '--json'])
    runs_data, runs_err = run_json(['openclaw', 'cron', 'runs', '--job', JOB_ID, '--json'])

    job = None
    for j in (jobs_data or {}).get('jobs', []):
        if j.get('id') == JOB_ID:
            job = j
            break

    state = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            state = {}

    entries = (runs_data or {}).get('entries', [])
    latest = entries[0] if entries else None

    payload = {
        'generatedAt': now_iso(),
        'jobId': JOB_ID,
        'job': {
            'name': (job or {}).get('name'),
            'enabled': (job or {}).get('enabled'),
            'schedule': (job or {}).get('schedule'),
            'lastStatus': ((job or {}).get('state') or {}).get('lastStatus'),
            'lastRunAtMs': ((job or {}).get('state') or {}).get('lastRunAtMs'),
            'nextRunAtMs': ((job or {}).get('state') or {}).get('nextRunAtMs'),
            'consecutiveErrors': ((job or {}).get('state') or {}).get('consecutiveErrors', 0),
        },
        'latestRun': latest,
        'recentRuns': entries[:20],
        'emailStateSummary': summarize_email_state(state),
        'errors': {
            'jobs': jobs_err,
            'runs': runs_err,
        }
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Wrote email guardrail snapshot')


if __name__ == '__main__':
    main()
