#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent
STATUS_PATH = ROOT / "status.json"
ACTIVITY_DIR = WORKSPACE / "memory" / "activity"
OUT_DIR = ROOT / "daily-cockpit" / "data"
OUT_PATH = OUT_DIR / "latest.json"

LOCAL_DAY_OFFSET_HOURS = -7  # Jon is in America/Los_Angeles; good enough for current DST season


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def today_local_date_iso() -> str:
    now_utc = datetime.now(timezone.utc)
    local = now_utc.timestamp() + (LOCAL_DAY_OFFSET_HOURS * 3600)
    return datetime.fromtimestamp(local, tz=timezone.utc).date().isoformat()


def load_activity_lines(day_iso: str):
    path = ACTIVITY_DIR / f"{day_iso}.md"
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- "):
            lines.append(line[2:].strip())
    return lines


def classify_job(job: dict) -> str:
    if not job.get("enabled", True):
        return "disabled"
    if job.get("consecutiveErrors", 0) >= 3:
        return "critical"
    if job.get("lastStatus") == "error" or job.get("consecutiveErrors", 0) > 0:
        return "warning"
    return "ok"


def next_jobs(jobs: list[dict], limit: int = 5):
    future = [j for j in jobs if j.get("nextRunAtMs")]
    future.sort(key=lambda j: j.get("nextRunAtMs") or 0)
    return future[:limit]


def main():
    status = load_json(STATUS_PATH, {}) or {}
    summary = status.get("summary") or {}
    usage = status.get("usage") or {}
    jobs = status.get("jobs") or []

    day_iso = today_local_date_iso()
    activity = load_activity_lines(day_iso)

    job_counts = {"ok": 0, "warning": 0, "critical": 0, "disabled": 0}
    for job in jobs:
        job_counts[classify_job(job)] += 1

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "day": day_iso,
        "headline": {
            "overall": summary.get("overall", "unknown"),
            "enabledJobs": summary.get("enabledJobs"),
            "emailSentTotal": summary.get("emailSentTotal"),
            "emailReceivedTotal": summary.get("emailReceivedTotal"),
            "slackSentTotal": summary.get("slackSentTotal"),
            "tokensToday": usage.get("tokensToday"),
            "trendVsYesterdayPct": usage.get("trendVsYesterdayPct"),
        },
        "jobCounts": job_counts,
        "nextJobs": [
            {
                "name": j.get("name"),
                "nextRunAtMs": j.get("nextRunAtMs"),
                "lastStatus": j.get("lastStatus"),
                "status": classify_job(j),
            }
            for j in next_jobs(jobs)
        ],
        "activity": {
            "count": len(activity),
            "items": activity,
        },
        "insights": [
            insight
            for insight in [
                f"{len(activity)} verified activity item(s) logged today." if activity else "No verified activity items logged yet today.",
                f"{job_counts['critical']} critical + {job_counts['warning']} warning job state(s).",
                "OpenClaw update available." if usage.get("updateAvailable") else None,
            ]
            if insight
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
