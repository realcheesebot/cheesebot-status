#!/usr/bin/env python3
import json
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "status.json"
WORKSPACE = ROOT.parent
EMAIL_SEND_LOG = WORKSPACE / "memory" / "email-send-log.jsonl"
EMAIL_STATE = WORKSPACE / "memory" / "email-state.json"
SLACK_SEND_LOG = WORKSPACE / "memory" / "slack-send-log.jsonl"
NOTIFIER_CONFIG = WORKSPACE / "config" / "notifier.json"
OPENCLAW_CFG = Path('/home/ubuntu/.openclaw/openclaw.json')
UPDATE_CHECK = Path('/home/ubuntu/.openclaw/update-check.json')
SESSIONS_FILE = Path('/home/ubuntu/.openclaw/agents/main/sessions/sessions.json')


def run_json(cmd, retries=3, timeout=20):
    last_err = None
    for _ in range(max(1, retries)):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            last_err = f"timeout after {timeout}s"
            continue
        if p.returncode == 0:
            try:
                return json.loads(p.stdout), None
            except Exception as e:
                last_err = f"json parse error: {e}"
        else:
            last_err = (p.stderr or p.stdout).strip()
    return None, last_err


def run_text(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {timeout}s", 124


def health_from_jobs(jobs):
    crit = 0
    warn = 0
    for j in jobs:
        st = (j.get("state") or {})
        effective_status = st.get("effectiveStatus") or st.get("lastStatus")
        if effective_status == "error":
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
    return token


def _slack_api(token: str, method: str, payload: dict, timeout=10):
    req = urllib.request.Request(
        url=f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def count_slack_sent_via_sdk(limit=200):
    token = _slack_bot_token()
    if not token:
        return None, "missing Slack bot token"

    target_user = _slack_target_user_id()
    if not target_user:
        return None, "missing slack.target_user_id in config/notifier.json"

    try:
        auth = _slack_api(token, "auth.test", {}, timeout=8)
        if not auth.get("ok"):
            return None, f"auth.test failed: {auth.get('error')}"
        bot_user_id = auth.get("user_id")

        opened = _slack_api(token, "conversations.open", {"users": target_user}, timeout=8)
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
            hist = _slack_api(token, "conversations.history", payload, timeout=8)
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


def load_session_metrics():
    if not SESSIONS_FILE.exists():
        return {"today": None, "sevenDay": None, "estimatedCostUsd": None, "model": None, "trendVsYesterday": None}, "sessions file missing"
    try:
        data = json.loads(SESSIONS_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        return {"today": None, "sevenDay": None, "estimatedCostUsd": None, "model": None, "trendVsYesterday": None}, str(e)

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    seven_ago = now - timedelta(days=7)

    today_total = 0
    yesterday_total = 0
    seven_total = 0
    cost_today = 0.0
    cost_7d = 0.0
    have_cost_today = False
    have_cost_7d = False
    active_model = None
    newest_updated = -1

    for key, sess in data.items():
        updated_at_ms = sess.get('updatedAt')
        if not isinstance(updated_at_ms, (int, float)):
            continue
        updated_dt = datetime.fromtimestamp(updated_at_ms / 1000, tz=timezone.utc)
        total_tokens = sess.get('totalTokens')
        if not isinstance(total_tokens, (int, float)):
            total_tokens = 0
        if updated_dt >= seven_ago:
            seven_total += int(total_tokens)
        if updated_dt >= day_ago:
            today_total += int(total_tokens)
        elif day_ago > updated_dt >= now - timedelta(days=2):
            yesterday_total += int(total_tokens)

        cost = sess.get('estimatedCostUsd')
        if isinstance(cost, (int, float)):
            if updated_dt >= seven_ago:
                cost_7d += float(cost)
                have_cost_7d = True
            if updated_dt >= day_ago:
                cost_today += float(cost)
                have_cost_today = True

        if key == 'agent:main:slack:direct:u03lqqb6l':
            active_model = sess.get('model') or active_model
        if updated_at_ms > newest_updated:
            newest_updated = updated_at_ms
            active_model = active_model or sess.get('model')

    trend = None
    if yesterday_total > 0:
        trend = round(((today_total - yesterday_total) / yesterday_total) * 100, 1)
    elif today_total > 0:
        trend = 100.0

    return {
        "today": today_total,
        "sevenDay": seven_total,
        "estimatedCostTodayUsd": round(cost_today, 4) if have_cost_today else None,
        "estimatedCost7dUsd": round(cost_7d, 4) if have_cost_7d else None,
        "model": active_model,
        "trendVsYesterday": trend,
    }, None


def parse_openclaw_status(text: str):
    import re

    version = None
    latest_version = None
    model = None
    for line in text.splitlines():
        if line.strip().startswith('│ Update'):
            parts = [p.strip() for p in line.split('│') if p.strip()]
            if len(parts) >= 2:
                update_text = parts[1]
                if 'npm latest' in update_text:
                    version_part, latest_part = update_text.split('npm latest', 1)
                    latest_version = latest_part.strip()
                    if 'up to date' in version_part:
                        version = latest_version
                elif 'installed' in update_text and 'latest' in update_text:
                    m = re.search(r'installed\s+([^·]+?)\s+·\s+.*latest\s+(.+)$', update_text)
                    if m:
                        version = m.group(1).strip()
                        latest_version = m.group(2).strip()
                else:
                    m = re.search(r'available\s+·\s+\S+\s+·\s+(?:npm\s+update|pnpm\s+update|update)\s+([0-9][0-9A-Za-z._-]*)', update_text)
                    if m:
                        latest_version = m.group(1).strip()
        if line.strip().startswith('│ agent:main:slack:direct:') or line.strip().startswith('│ agent:main:main'):
            m = line.split('│')
            if len(m) >= 5:
                candidate = m[4].strip()
                if candidate:
                    model = candidate
                    if 'slack:direct' in line:
                        break
    return version, latest_version, model


def load_openclaw_version_fallback():
    if not UPDATE_CHECK.exists():
        return None
    try:
        data = json.loads(UPDATE_CHECK.read_text(encoding='utf-8'))
        return data.get('lastNotifiedVersion')
    except Exception:
        return None


def load_all_jobs_with_fallback():
    cron_data, cron_err = run_json(["openclaw", "cron", "list", "--all", "--json"])
    cli_jobs = (cron_data or {}).get("jobs", [])

    file_jobs = []
    file_err = None
    cron_jobs_path = Path('/home/ubuntu/.openclaw/cron/jobs.json')
    try:
        if cron_jobs_path.exists():
            raw = json.loads(cron_jobs_path.read_text(encoding='utf-8'))
            file_jobs = (raw or {}).get('jobs') or []
    except Exception as e:
        file_err = str(e)

    if file_jobs and len(file_jobs) >= len(cli_jobs):
        return file_jobs, cron_err, file_err, 'disk_fallback'
    return cli_jobs, cron_err, file_err, 'cli'


def main():
    now = datetime.now(timezone.utc).isoformat()
    jobs, cron_err, cron_file_err, cron_source = load_all_jobs_with_fallback()

    enabled = [j for j in jobs if j.get("enabled", True)]
    disabled = [j for j in jobs if not j.get("enabled", True)]

    openclaw_out, openclaw_err, openclaw_rc = run_text(["openclaw", "status"], timeout=15)
    openclaw_version, latest_openclaw_version, status_model = parse_openclaw_status(openclaw_out)
    if not openclaw_version:
        openclaw_version = load_openclaw_version_fallback()
    if not latest_openclaw_version:
        latest_openclaw_version = load_openclaw_version_fallback()

    token_metrics, token_err = load_session_metrics()
    if not token_metrics.get('model'):
        token_metrics['model'] = status_model

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

    email_compliance_error = None
    email_pending_required = 0
    try:
        if EMAIL_STATE.exists():
            email_state = json.loads(EMAIL_STATE.read_text(encoding='utf-8'))
            pending = email_state.get('lastGuardrailPending') or []
            if isinstance(pending, list):
                email_pending_required = len(pending)
                if email_pending_required > 0:
                    email_compliance_error = f'{email_pending_required} unresolved required replies'
    except Exception as e:
        email_compliance_error = f'email compliance read error: {e}'

    effective_enabled = []
    for j in enabled:
        clone = dict(j)
        state = dict((j.get('state') or {}))
        if j.get('name') == 'email-guardrail-check' and email_compliance_error:
            state['effectiveStatus'] = 'error'
            state['complianceError'] = email_compliance_error
            clone['state'] = state
        effective_enabled.append(clone)

    report = {
        "generatedAt": now,
        "summary": {
            "overall": health_from_jobs(effective_enabled),
            "enabledJobs": len(enabled),
            "disabledJobs": len(disabled),
            "totalJobs": len(jobs),
            "emailSentTotal": email_sent_total,
            "emailSentCountSource": email_sent_source,
            "emailReceivedTotal": email_received_total,
            "emailPendingRequiredReplies": email_pending_required,
            "slackSentTotal": slack_sent_total,
            "slackSentCountSource": slack_count_source,
        },
        "usage": {
            "tokensToday": token_metrics.get('today'),
            "tokens7d": token_metrics.get('sevenDay'),
            "trendVsYesterdayPct": token_metrics.get('trendVsYesterday'),
            "estimatedCostTodayUsd": token_metrics.get('estimatedCostTodayUsd'),
            "estimatedCost7dUsd": token_metrics.get('estimatedCost7dUsd'),
            "model": token_metrics.get('model') or status_model,
            "openclawVersion": openclaw_version,
            "latestOpenclawVersion": latest_openclaw_version,
            "updateAvailable": bool(openclaw_version and latest_openclaw_version and openclaw_version != latest_openclaw_version),
        },
        "checks": {
            "cronList": "ok" if cron_err is None else "error",
            "openclawStatus": "ok" if openclaw_rc == 0 else "error",
            "tokenMetrics": "ok" if token_err is None else "error",
            "emailCompliance": "error" if email_compliance_error else "ok",
        },
        "errors": {
            "cron": cron_err,
            "cronFile": cron_file_err,
            "openclaw": openclaw_err if openclaw_rc != 0 else None,
            "slackCountApi": slack_api_err,
            "tokenMetrics": token_err,
            "emailCompliance": email_compliance_error,
        },
        "jobs": [
            {
                "name": j.get("name"),
                "enabled": j.get("enabled"),
                "schedule": j.get("schedule"),
                "nextRunAtMs": (j.get("state") or {}).get("nextRunAtMs"),
                "lastStatus": ((j.get("state") or {}).get("effectiveStatus") or (j.get("state") or {}).get("lastStatus")),
                "rawLastStatus": (j.get("state") or {}).get("lastStatus"),
                "consecutiveErrors": (j.get("state") or {}).get("consecutiveErrors", 0),
                "complianceError": (j.get("state") or {}).get("complianceError"),
            }
            for j in (effective_enabled + disabled)
        ],
        "raw": {
            "openclawStatusSnippet": openclaw_out[:1200],
            "cronSource": cron_source,
        },
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
