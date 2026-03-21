#!/usr/bin/env python3
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "status.json"
WORKSPACE = ROOT.parent
EMAIL_SEND_LOG = WORKSPACE / "memory" / "email-send-log.jsonl"
EMAIL_STATE = WORKSPACE / "memory" / "email-state.json"
SLACK_SEND_LOG = WORKSPACE / "memory" / "slack-send-log.jsonl"
NOTIFIER_CONFIG = WORKSPACE / "config" / "notifier.json"
OPENCLAW_CFG = Path('/home/ubuntu/.openclaw/openclaw.json')


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


def count_sent_emails_from_state(path: Path):
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    msgs = (data or {}).get("messages")
    if not isinstance(msgs, dict):
        return None
    return sum(1 for m in msgs.values() if isinstance(m, dict) and m.get("repliedAt"))


def _slack_target_user_id():
    try:
        cfg = json.loads(NOTIFIER_CONFIG.read_text(encoding="utf-8")) if NOTIFIER_CONFIG.exists() else {}
        return ((cfg or {}).get("slack") or {}).get("target_user_id")
    except Exception:
        return None


def _slack_bot_token():
    try:
        cfg = json.loads(OPENCLAW_CFG.read_text(encoding="utf-8")) if OPENCLAW_CFG.exists() else {}
    except Exception:
        cfg = {}
    token = (((cfg.get("channels") or {}).get("slack") or {}).get("botToken"))
    return token or os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN")


def _slack_api(token: str, method: str, payload: dict):
    req = urllib.request.Request(
        url=f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def count_slack_sent_via_sdk(limit=None):
    token = _slack_bot_token()
    if not token:
        return None, "missing Slack bot token"

    target_user = _slack_target_user_id()
    if not target_user:
        return None, "missing slack.target_user_id in config/notifier.json"

    try:
        auth = _slack_api(token, "auth.test", {})
        if not auth.get("ok"):
            return None, f"auth.test failed: {auth.get('error')}"
        bot_user_id = auth.get("user_id")

        opened = _slack_api(token, "conversations.open", {"users": target_user})
        if not opened.get("ok"):
            return None, f"conversations.open failed: {opened.get('error')}"
        channel_id = ((opened.get("channel") or {}).get("id"))
        if not channel_id:
            return None, "failed to resolve DM channel id"

        count = 0
        cursor = None
        page_size = 200
        while True:
            payload = {"channel": channel_id, "limit": page_size}
            if cursor:
                payload["cursor"] = cursor
            hist = _slack_api(token, "conversations.history", payload)
            if not hist.get("ok"):
                return None, f"conversations.history failed: {hist.get('error')}"
            messages = hist.get("messages") or []
            for m in messages:
                if m.get("user") == bot_user_id or m.get("bot_id"):
                    count += 1
                    if limit is not None and count >= limit:
                        break
            if limit is not None and count >= limit:
                break
            cursor = ((hist.get("response_metadata") or {}).get("next_cursor"))
            if not cursor:
                break
        return count, None
    except Exception as e:
        return None, str(e)


def main():
    now = datetime.now(timezone.utc).isoformat()
    cron_data, cron_err = run_json(["openclaw", "cron", "list", "--json"])
    jobs = (cron_data or {}).get("jobs", [])

    enabled = [j for j in jobs if j.get("enabled", True)]
    disabled = [j for j in jobs if not j.get("enabled", True)]

    openclaw_out, openclaw_err, openclaw_rc = run_text(["openclaw", "status"])

    email_sent_from_state = count_sent_emails_from_state(EMAIL_STATE)
    if email_sent_from_state is None:
        email_sent_total = count_jsonl_rows(EMAIL_SEND_LOG)
        email_sent_source = "jsonl_fallback"
    else:
        email_sent_total = email_sent_from_state
        email_sent_source = "email_state_repliedAt"

    email_received_total = count_received_emails(EMAIL_STATE)

    slack_sent_api_total, slack_api_err = count_slack_sent_via_sdk()
    if slack_sent_api_total is None:
        slack_sent_total = count_jsonl_rows(SLACK_SEND_LOG)
        slack_count_source = "jsonl_fallback"
    else:
        slack_sent_total = slack_sent_api_total
        slack_count_source = "slack_sdk_dm_history"

    report = {
        "generatedAt": now,
        "summary": {
            "overall": health_from_jobs(enabled),
            "enabledJobs": len(enabled),
            "disabledJobs": len(disabled),
            "totalJobs": len(jobs),
            "emailSentTotal": email_sent_total,
            "emailSentCountSource": email_sent_source,
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
