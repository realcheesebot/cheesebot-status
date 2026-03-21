#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT.parent / 'memory' / 'email-send-log.jsonl'
OUT = ROOT / 'weather-reports' / 'data' / 'overview.json'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if LOG.exists():
        for line in LOG.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            subj = (j.get('subject') or '')
            if 'weather' in subj.lower():
                rows.append(j)

    rows.sort(key=lambda x: x.get('ts', 0), reverse=True)
    latest = rows[0] if rows else None

    payload = {
        'generatedAt': now_iso(),
        'count': len(rows),
        'latest': latest,
        'recent': rows[:30],
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Wrote weather snapshot')


if __name__ == '__main__':
    main()
