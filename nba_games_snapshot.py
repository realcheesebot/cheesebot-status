#!/usr/bin/env python3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / 'nba-daily-games' / 'data'
SCHEDULE_URL = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def day_key(dt_utc):
    return dt_utc.strftime('%Y-%m-%d')


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    r = requests.get(SCHEDULE_URL, timeout=45)
    r.raise_for_status()
    data = r.json()
    games = (((data.get('leagueSchedule') or {}).get('gameDates')) or [])

    now = datetime.now(timezone.utc)
    today = day_key(now)
    tomorrow = day_key(now + timedelta(days=1))

    picked = []
    for gd in games:
        raw = (gd.get('gameDate') or '').strip()
        # schedule uses MM/DD/YYYY HH:MM:SS
        try:
            d = datetime.strptime(raw.split()[0], '%m/%d/%Y').strftime('%Y-%m-%d')
        except Exception:
            continue
        if d not in (today, tomorrow):
            continue
        for g in gd.get('games') or []:
            away = ((g.get('awayTeam') or {}).get('teamTricode') or '')
            home = ((g.get('homeTeam') or {}).get('teamTricode') or '')
            tip = g.get('gameDateTimeUTC')
            picked.append({
                'date': d,
                'matchup': f'{away}@{home}',
                'tipoffUtc': tip,
                'gameId': g.get('gameId'),
                'arena': ((g.get('arena') or {}).get('arenaName')),
            })

    picked.sort(key=lambda x: (x.get('date') or '', x.get('tipoffUtc') or ''))

    summary = {
        'generatedAt': iso_now(),
        'today': today,
        'tomorrow': tomorrow,
        'count': len(picked),
        'games': picked,
    }

    (OUT_DIR / 'overview.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Wrote nba-daily-games data snapshot')


if __name__ == '__main__':
    main()
