#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'self-audit' / 'data' / 'overview.json'
JOB_NAME = 'daily-10am-self-audit'


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


def summarize_runs(entries):
    ok = 0
    err = 0
    other = 0
    for e in entries:
        st = (e or {}).get('status')
        if st == 'ok':
            ok += 1
        elif st == 'error':
            err += 1
        else:
            other += 1
    return {'ok': ok, 'error': err, 'other': other, 'total': len(entries)}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    jobs_data, jobs_err = run_json(['openclaw', 'cron', 'list', '--json'])
    jobs = (jobs_data or {}).get('jobs', [])
    job = next((j for j in jobs if j.get('name') == JOB_NAME), None)

    runs_data = None
    runs_err = None
    entries = []
    if job and job.get('id'):
        runs_data, runs_err = run_json(['openclaw', 'cron', 'runs', '--id', job.get('id')])
        entries = (runs_data or {}).get('entries', [])

    state = (job or {}).get('state') or {}
    payload = {
        'generatedAt': now_iso(),
        'jobName': JOB_NAME,
        'jobId': (job or {}).get('id'),
        'job': {
            'enabled': (job or {}).get('enabled'),
            'schedule': (job or {}).get('schedule'),
            'lastStatus': state.get('lastStatus'),
            'lastRunAtMs': state.get('lastRunAtMs'),
            'nextRunAtMs': state.get('nextRunAtMs'),
            'consecutiveErrors': state.get('consecutiveErrors', 0),
        },
        'latestRun': entries[0] if entries else None,
        'recentRuns': entries[:30],
        'runSummary': summarize_runs(entries[:30]),
        'errors': {
            'jobs': jobs_err,
            'runs': runs_err,
            'jobNotFound': None if job else f'job not found by name: {JOB_NAME}',
        },
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Wrote self-audit snapshot')


if __name__ == '__main__':
    main()
