#!/usr/bin/env python3
import base64
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
LOG = ROOT.parent / 'memory' / 'email-send-log.jsonl'
OUT = ROOT / 'stocks' / 'data' / 'overview.json'
QUOTA_PROJECT = 'cheesebot-488123'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gmail_token():
    p = subprocess.run(['gcloud', 'auth', 'application-default', 'print-access-token'], capture_output=True, text=True)
    return (p.stdout or '').strip()


def extract_html_part(payload):
    if not payload:
        return None
    if payload.get('mimeType') == 'text/html' and (payload.get('body') or {}).get('data'):
        return payload['body']['data']
    for part in payload.get('parts') or []:
        got = extract_html_part(part)
        if got:
            return got
    return None


def fetch_report_text(message_id):
    tok = gmail_token()
    if not tok or not message_id:
        return None
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full'
    r = requests.get(url, headers={'Authorization': f'Bearer {tok}', 'X-Goog-User-Project': QUOTA_PROJECT}, timeout=30)
    if r.status_code >= 300:
        return None
    msg = r.json()
    raw = extract_html_part(msg.get('payload'))
    if not raw:
        return None
    body = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8', 'ignore')
    m = re.search(r'<pre[^>]*>(.*?)</pre>', body, flags=re.I | re.S)
    if m:
        body = m.group(1)
    body = re.sub(r'<br\s*/?>', '\n', body, flags=re.I)
    body = re.sub(r'</p>', '\n', body, flags=re.I)
    body = re.sub(r'<[^>]+>', '', body)
    return html.unescape(body).strip()


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
            if 'stock' in subj.lower():
                rows.append(j)

    rows.sort(key=lambda x: x.get('ts', 0), reverse=True)
    latest = rows[0] if rows else None

    latest_report_text = None
    if latest:
        sent = latest.get('sent') or []
        msg_id = (sent[0] or {}).get('id') if sent else None
        latest_report_text = fetch_report_text(msg_id)

    payload = {
        'generatedAt': now_iso(),
        'count': len(rows),
        'latest': latest,
        'latestReportText': latest_report_text,
        'recent': rows[:30],
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print('Wrote stocks snapshot')


if __name__ == '__main__':
    main()
