#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "status.json"


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


def main():
    now = datetime.now(timezone.utc).isoformat()
    cron_data, cron_err = run_json(["openclaw", "cron", "list", "--json"])
    jobs = (cron_data or {}).get("jobs", [])

    enabled = [j for j in jobs if j.get("enabled", True)]
    disabled = [j for j in jobs if not j.get("enabled", True)]

    openclaw_out, openclaw_err, openclaw_rc = run_text(["openclaw", "status"])

    report = {
        "generatedAt": now,
        "summary": {
            "overall": health_from_jobs(enabled),
            "enabledJobs": len(enabled),
            "disabledJobs": len(disabled),
            "totalJobs": len(jobs),
        },
        "checks": {
            "cronList": "ok" if cron_err is None else "error",
            "openclawStatus": "ok" if openclaw_rc == 0 else "error",
        },
        "errors": {
            "cron": cron_err,
            "openclaw": openclaw_err if openclaw_rc != 0 else None,
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
