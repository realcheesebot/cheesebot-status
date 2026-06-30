#!/usr/bin/env python3
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'self-audit' / 'data' / 'overview.json'
STATUS_JSON = ROOT / 'status.json'
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


def classify_issue_severity(text):
    t = (text or '').lower()
    if (
        'self_audit_email_only' in t
        or '--no-slack-notify' in t
        or 'do not send the report to slack' in t
        or 'do not call slack_notify.py' in t
        or 'email_notify.py' in t
    ):
        return 'info'
    if any(k in t for k in ['critical', 'failed', 'failure', 'error', 'hard stop']):
        return 'critical'
    if any(k in t for k in ['warn', 'drift', 'mismatch', 'contradiction', 'disabled']):
        return 'warning'
    return 'info'


def parse_latest_summary(summary_text):
    if not summary_text:
        return {
            'text': None,
            'findings': [],
            'checksMentioned': [],
            'constraints': [],
            'actions': [],
        }

    lines = [ln.strip() for ln in summary_text.splitlines() if ln.strip()]
    findings = []
    checks = []
    constraints = []
    actions = []

    check_terms = [
        ('cron status', 'cron status'),
        ('guardrail', 'permanent rules/guardrails'),
        ('health snapshot', 'system health snapshot'),
        ('drift', 'drift/contradictions'),
        ('contradiction', 'drift/contradictions'),
        ('corrective action', 'corrective actions'),
        ('email only', 'email-only delivery'),
        ('email_notify.py', 'email notifier delivery'),
        ('no slack', 'slack report disabled'),
    ]

    for ln in lines:
        low = ln.lower()
        if re.search(r'\b(mode|hard stop|never|send|deliver|include|produce)\b', low):
            findings.append({'text': ln, 'severity': classify_issue_severity(ln)})

        for needle, label in check_terms:
            if needle in low and label not in checks:
                checks.append(label)

        if 'email only' in low or 'do not send the report to slack' in low or 'do not call slack_notify.py' in low:
            constraints.append(ln)

        if 'send it via' in low or 'deliver by' in low or 'corrective' in low or 'email_notify.py' in low:
            actions.append(ln)

    return {
        'text': summary_text,
        'findings': findings[:20],
        'checksMentioned': checks,
        'constraints': constraints[:10],
        'actions': actions[:10],
    }


def build_global_health(jobs):
    enabled = [j for j in jobs if j.get('enabled', True)]
    consecutive_error_jobs = []
    last_error_jobs = []
    for j in enabled:
        st = (j.get('state') or {})
        if (st.get('consecutiveErrors') or 0) > 0:
            consecutive_error_jobs.append({
                'name': j.get('name'),
                'consecutiveErrors': st.get('consecutiveErrors') or 0,
                'lastStatus': st.get('lastStatus'),
            })
        if st.get('lastStatus') == 'error':
            last_error_jobs.append(j.get('name'))

    if any((x.get('consecutiveErrors') or 0) >= 3 for x in consecutive_error_jobs):
        overall = 'critical'
    elif consecutive_error_jobs or last_error_jobs:
        overall = 'warning'
    else:
        overall = 'ok'

    return {
        'overall': overall,
        'enabledJobs': len(enabled),
        'totalJobs': len(jobs),
        'jobsWithConsecutiveErrors': consecutive_error_jobs,
        'jobsWithLastError': last_error_jobs,
    }


def build_checks(job, entries, jobs, latest_summary):
    state = (job or {}).get('state') or {}
    job_text = (((job or {}).get('payload') or {}).get('text') or '')
    job_text_lower = job_text.lower()
    checks = []

    checks.append({
        'name': 'Self-audit job exists',
        'status': 'pass' if job else 'fail',
        'detail': 'Found by name in cron list' if job else 'Job not found in cron list',
    })
    checks.append({
        'name': 'Self-audit job enabled',
        'status': 'pass' if (job or {}).get('enabled') else 'fail',
        'detail': f"enabled={(job or {}).get('enabled')}",
    })
    checks.append({
        'name': 'Last run status',
        'status': 'pass' if state.get('lastStatus') == 'ok' else 'warn',
        'detail': f"lastStatus={state.get('lastStatus')}",
    })
    checks.append({
        'name': 'Consecutive errors',
        'status': 'pass' if (state.get('consecutiveErrors') or 0) == 0 else 'warn',
        'detail': f"consecutiveErrors={state.get('consecutiveErrors') or 0}",
    })

    recent = entries[:7]
    recent_ok = sum(1 for e in recent if (e or {}).get('status') == 'ok')
    checks.append({
        'name': 'Recent run reliability (last 7)',
        'status': 'pass' if recent and recent_ok == len(recent) else ('warn' if recent else 'warn'),
        'detail': f"okRuns={recent_ok}/{len(recent)}",
    })

    checks.append({
        'name': 'Email-only delivery configured',
        'status': 'pass' if (
            'self_audit_email_only' in job_text_lower
            and 'email_notify.py' in job_text_lower
            and '--no-slack-notify' in job_text_lower
            and 'jon@silverpine.com' in job_text_lower
        ) else 'fail',
        'detail': 'Cron payload sends the audit by email only to Jon' if (
            'self_audit_email_only' in job_text_lower
            and 'email_notify.py' in job_text_lower
            and '--no-slack-notify' in job_text_lower
            and 'jon@silverpine.com' in job_text_lower
        ) else 'Cron payload is missing the expected email-only delivery instructions',
    })
    checks.append({
        'name': 'Slack report disabled',
        'status': 'pass' if (
            'scripts/slack_notify.py' not in job_text_lower
            and (
                'do not send the report to slack' in job_text_lower
                or 'do not call slack_notify.py' in job_text_lower
            )
        ) else 'fail',
        'detail': 'Cron payload disables Slack report delivery' if (
            'scripts/slack_notify.py' not in job_text_lower
            and (
                'do not send the report to slack' in job_text_lower
                or 'do not call slack_notify.py' in job_text_lower
            )
        ) else 'Cron payload still allows or references Slack report delivery',
    })

    critical_job_errors = []
    for j in jobs:
        st = (j.get('state') or {})
        if (st.get('consecutiveErrors') or 0) >= 3:
            critical_job_errors.append(j.get('name'))

    checks.append({
        'name': 'No critical cron degradation',
        'status': 'pass' if not critical_job_errors else 'fail',
        'detail': 'No enabled jobs with >=3 consecutive errors' if not critical_job_errors else f"Critical jobs: {', '.join(critical_job_errors)}",
    })

    status_summary = (((latest_summary or {}).get('statusSnapshotSummary')) or {}) if isinstance(latest_summary, dict) else {}
    pending_required = status_summary.get('emailPendingRequiredReplies')
    checks.append({
        'name': 'No unresolved required email replies',
        'status': 'pass' if not pending_required else 'fail',
        'detail': 'No unresolved required replies in compliance state' if not pending_required else f'unresolved required replies={pending_required}',
    })

    return checks


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    jobs_data, jobs_err = run_json(['openclaw', 'cron', 'list', '--all', '--json'])
    jobs = (jobs_data or {}).get('jobs', [])
    job = next((j for j in jobs if j.get('name') == JOB_NAME), None)

    runs_data = None
    runs_err = None
    entries = []
    if job and job.get('id'):
        runs_data, runs_err = run_json(['openclaw', 'cron', 'runs', '--id', job.get('id')])
        entries = (runs_data or {}).get('entries', [])

    status_json = {}
    status_json_err = None
    if STATUS_JSON.exists():
        try:
            status_json = json.loads(STATUS_JSON.read_text(encoding='utf-8'))
        except Exception as e:
            status_json_err = str(e)
    else:
        status_json_err = 'status.json not found'

    state = (job or {}).get('state') or {}
    latest_run = entries[0] if entries else None
    latest_summary = parse_latest_summary((latest_run or {}).get('summary'))
    latest_summary['statusSnapshotSummary'] = (status_json or {}).get('summary') or {}
    run_summary = summarize_runs(entries[:30])
    checks = build_checks(job, entries, jobs, latest_summary)

    check_counts = {
        'pass': sum(1 for c in checks if c.get('status') == 'pass'),
        'warn': sum(1 for c in checks if c.get('status') == 'warn'),
        'fail': sum(1 for c in checks if c.get('status') == 'fail'),
        'total': len(checks),
    }

    findings = list(latest_summary.get('findings') or [])
    for c in checks:
        if c.get('status') in ('warn', 'fail'):
            findings.append({
                'text': f"{c.get('name')}: {c.get('detail')}",
                'severity': 'critical' if c.get('status') == 'fail' else 'warning',
            })

    global_health = build_global_health(jobs)

    all_jobs = []
    for j in jobs:
        st = (j.get('state') or {})
        all_jobs.append({
            'name': j.get('name'),
            'enabled': j.get('enabled'),
            'schedule': j.get('schedule'),
            'lastStatus': st.get('lastStatus'),
            'consecutiveErrors': st.get('consecutiveErrors', 0),
            'lastRunAtMs': st.get('lastRunAtMs'),
            'nextRunAtMs': st.get('nextRunAtMs'),
        })

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
        'health': {
            'overall': global_health.get('overall'),
            'checks': check_counts,
            'issuesFound': len(findings),
            'actionsPending': check_counts['warn'] + check_counts['fail'],
            'actionsTaken': run_summary.get('ok', 0),
            'cron': global_health,
            'statusSnapshotSummary': (status_json or {}).get('summary'),
        },
        'checksPerformed': checks,
        'latestRun': latest_run,
        'latestRunSummary': latest_summary,
        'recentRuns': entries[:30],
        'runSummary': run_summary,
        'driftAndContradictions': findings[:50],
        'correctiveActions': [
            {'type': 'automated', 'detail': 'Daily self-audit cron job is scheduled and active.' if (job or {}).get('enabled') else 'Self-audit job not enabled.'},
            {'type': 'automated', 'detail': 'Run health trend captured from recent executions.'},
            {'type': 'recommended', 'detail': 'Investigate any WARN/FAIL checks listed above and remediate drift.'},
        ],
        'allJobs': all_jobs,
        'errors': {
            'jobs': jobs_err,
            'runs': runs_err,
            'jobNotFound': None if job else f'job not found by name: {JOB_NAME}',
            'statusJson': status_json_err,
        },
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Wrote self-audit snapshot')


if __name__ == '__main__':
    main()
