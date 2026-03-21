#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT.parent / 'data' / 'nba_injury_watch_state.json'
OUT_DIR = ROOT / 'injury-report' / 'data'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def parse_key(k: str):
    # Team|gameId|tipoffIso
    parts = k.split('|')
    if len(parts) != 3:
        return {'team': k, 'gameId': None, 'tipoff': None}
    return {'team': parts[0], 'gameId': parts[1], 'tipoff': parts[2]}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    teams_dir = OUT_DIR / 'teams'
    teams_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'sent': {}}
    sent = data.get('sent') or {}

    rows = []
    by_team = defaultdict(list)

    for key, rec in sent.items():
        parsed = parse_key(key)
        row = {
            'key': key,
            'team': parsed['team'],
            'gameId': parsed['gameId'],
            'tipoff': parsed['tipoff'],
            'sentAt': rec.get('sentAt'),
            'matchup': rec.get('matchup'),
            'recipients': rec.get('recipients', []),
            'emailIds': rec.get('emailIds', []),
        }
        rows.append(row)
        by_team[parsed['team']].append(row)

    rows.sort(key=lambda r: r.get('sentAt') or '', reverse=True)
    for t in by_team:
        by_team[t].sort(key=lambda r: r.get('sentAt') or '', reverse=True)

    overview = {
        'generatedAt': iso_now(),
        'totalReports': len(rows),
        'teams': [],
        'latest': rows[0] if rows else None,
    }

    for team, items in sorted(by_team.items()):
        latest = items[0] if items else None
        team_slug = 'por' if 'Portland' in team else ('sas' if 'San Antonio' in team else team.lower().replace(' ', '-'))
        summary = {
            'team': team,
            'slug': team_slug,
            'count': len(items),
            'latest': latest,
        }
        overview['teams'].append(summary)

        (teams_dir / f'{team_slug}.json').write_text(json.dumps({
            'generatedAt': iso_now(),
            'team': team,
            'slug': team_slug,
            'count': len(items),
            'latest': latest,
            'history': items[:50],
        }, indent=2), encoding='utf-8')

    (OUT_DIR / 'overview.json').write_text(json.dumps(overview, indent=2), encoding='utf-8')
    (OUT_DIR / 'history.json').write_text(json.dumps({'generatedAt': iso_now(), 'rows': rows[:200]}, indent=2), encoding='utf-8')
    print('Wrote injury-report data snapshots')


if __name__ == '__main__':
    main()
