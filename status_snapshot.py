#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "status.json"
WORKSPACE = ROOT.parent
EMAIL_SEND_LOG = WORKSPACE / "memory" / "email-send-log.jsonl"
EMAIL_STATE = WORKSPACE / "memory" / "email-state.json"
SLACK_SEND_LOG = WORKSPACE / "memory" / "slack-send-log.jsonl"


def run_json(cmd, retries=3):
    last_err = None
    for _ in range(max(1, retries)):
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            try:
                return json.loads(p.stdout), None
            except Exception as e:
                last_err = f"json parse error: {e}"
        else:
            last_err = (p.stderr or p.stdout).strip()
    return None, last_err


def run_text(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode


def health_from_jobs(jobs):
    crit = 0
    warn = 0
    for j in jobs:
        st = (j.get("state") or {})
        if st.get("lastStatus") == "error":
            if (st.get("consecutiveErrors") or 0) >= 3:
                crit += 1
            else:
                warn += 1
    if crit:
        return "critical"
    if warn:
        return "warning"
    return "ok"


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
    except Exception:
        return 0
    return n


def count_received_emails(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    msgs = (data or {}).get("messages")
    return len(msgs) if isinstance(msgs, dict) else 0


def count_slack_sent_via_api(limit=1000):
    data, err = run_json([
        "openclaw", "message", "read",
        "--channel", "slack",
        "--from-me",
        "--limit", str(limit),
        "--json",
    ])
    if err:
        return None, err
    msgs = (data or {}).get("messages")
    if not isinstance(msgs, list):
        return 0, None
    return len(msgs), None


def main():
    now = datetime.now(timezone.utc).isoformat()
    cron_data, cron_err = run_json(["openclaw", "cron", "list", "--json"])
    jobs = (cron_data or {}).get("jobs", [])

    enabled = [j for j in jobs if j.get("enabled", True)]
    disabled = [j for j in jobs if not j.get("enabled", True)]

    openclaw_out, openclaw_err, openclaw_rc = run_text(["openclaw", "status"])

    email_sent_total = count_jsonl_rows(EMAIL_SEND_LOG)
    email_received_total = count_received_emails(EMAIL_STATE)

    slack_sent_api_total, slack_api_err = count_slack_sent_via_api(limit=1000)
    if slack_sent_api_total is None:
        slack_sent_total = count_jsonl_rows(SLACK_SEND_LOG)
        slack_count_source = "jsonl_fallback"
    else:
        slack_sent_total = slack_sent_api_total
        slack_count_source = "slack_api_from_me"

    report = {
        "generatedAt": now,
        "summary": {
            "overall": health_from_jobs(enabled),
            "enabledJobs": len(enabled),
            "disabledJobs": len(disabled),
            "totalJobs": len(jobs),
            "emailSentTotal": email_sent_total,
            "emailReceivedTotal": email_received_total,
            "slackSentTotal": slack_sent_total,
            "slackSentCountSource": slack_count_source,
        },
        "checks": {
            "cronList": "ok" if cron_err is None else "error",
            "openclawStatus": "ok" if openclaw_rc == 0 else "error",
        },
        "errors": {
            "cron": cron_err,
            "openclaw": openclaw_err if openclaw_rc != 0 else None,
            "slackCountApi": slack_api_err,
        },
        "jobs": [
            {
                "name": j.get("name"),
                "enabled": j.get("enabled"),
                "schedule": j.get("schedule"),
                "nextRunAtMs": (j.get("state") or {}).get("nextRunAtMs"),
                "lastStatus": (j.get("state") or {}).get("lastStatus"),
                "consecutiveErrors": (j.get("state") or {}).get("consecutiveErrors", 0),
            }
            for j in jobs
        ],
        "raw": {
            "openclawStatusSnippet": openclaw_out[:1200],
        },
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
