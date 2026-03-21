#!/usr/bin/env python3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / 'nba-daily-games' / 'data'
SCHEDULE_URL = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json'
STANDINGS_URL = 'https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2025-26&SeasonType=Regular+Season&SeasonYear='
ESPN_STANDINGS_URL = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def day_key(dt_utc):
    return dt_utc.strftime('%Y-%m-%d')


def fetch_west_standings():
    # Prefer ESPN standings for reliability.
    r = requests.get(ESPN_STANDINGS_URL, timeout=30)
    r.raise_for_status()
    j = r.json()
    children = j.get('children') or []
    west = None
    for c in children:
        abbr = ((c.get('abbreviation') or '')).upper()
        name = (c.get('name') or '').lower()
        if abbr == 'W' or 'western' in name:
            west = c
            break
    if not west:
        return []

    entries = west.get('standings', {}).get('entries', [])
    out = []
    for e in entries:
        team = (e.get('team') or {}).get('displayName') or ''
        stats = {s.get('name'): s.get('value') for s in (e.get('stats') or []) if s.get('name')}
        out.append({
            'rank': stats.get('playoffSeed') or stats.get('conferenceRank'),
            'team': team,
            'wins': stats.get('wins'),
            'losses': stats.get('losses'),
            'gb': stats.get('gamesBehind') if stats.get('gamesBehind') is not None else stats.get('playoffGamesBack'),
            'streak': stats.get('streak') or stats.get('lastTenGames'),
        })
    def rank_num(v):
        try:
            return int(float(v))
        except Exception:
            return 999
    out.sort(key=lambda x: rank_num(x.get('rank')))
    return out


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

    try:
        west = fetch_west_standings()
    except Exception:
        west = []

    summary = {
        'generatedAt': iso_now(),
        'today': today,
        'tomorrow': tomorrow,
        'count': len(picked),
        'games': picked,
        'westStandings': west,
    }

    (OUT_DIR / 'overview.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('Wrote nba-daily-games data snapshot')


if __name__ == '__main__':
    main()
