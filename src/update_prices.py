#!/usr/bin/env python3
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/home/moose/projects/m2')
DATA_DIR = BASE / 'data'
SNAP_DIR = DATA_DIR / 'snapshots'
STATE_FILE = DATA_DIR / 'last_published_date.txt'
LATEST_FILE = DATA_DIR / 'latest.json'

UA = {'User-Agent': 'Mozilla/5.0'}


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')


def fred_series(series_id: str):
    txt = http_get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}')
    out = {}
    for row in csv.DictReader(io.StringIO(txt)):
        d = row['observation_date']
        v = row.get(series_id, '')
        if v and v != '.':
            out[d] = float(v)
    return out


def _month_year_candidates(now: datetime):
    y, m = now.year, now.month
    prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
    return [(m, y), (prev_m, prev_y)]


def fetch_tsp_latest(now: datetime):
    """Fetch latest TSP C/S/I/G/F prices from tspdatacenter.
    Tries current month first, then previous month.
    """
    last_err = None
    for month, year in _month_year_candidates(now):
        try:
            html = http_get(
                f'https://www.tspdatacenter.com/daily-share-prices/?tsp_month={month}&tsp_year={year}'
            )
            m = re.search(r'<h3>([^<]+)</h3>\s*<table[^>]*>(.*?)</table>', html, re.S)
            if not m:
                raise RuntimeError('Could not parse latest TSP table block')

            human_date = m.group(1).strip()
            table = m.group(2)
            trade_date = datetime.strptime(human_date, '%A, %B %d, %Y').date().isoformat()

            pairs = re.findall(r'<b>([^<]+)</b>\s*&nbsp;\s*</td>\s*<td>\s*\$([0-9.]+)', table, re.S)
            data = {name.strip(): float(val) for name, val in pairs}
            funds = {
                'C': data.get('C Fund'),
                'S': data.get('S Fund'),
                'I': data.get('I Fund'),
                'G': data.get('G Fund'),
                'F': data.get('F Fund'),
            }
            return trade_date, funds
        except Exception as e:
            last_err = e
    raise RuntimeError(f'Failed to fetch TSP latest prices: {last_err}')


def fetch_fed_for_date(d: str):
    dff = fred_series('DFF')
    low = fred_series('DFEDTARL')
    high = fred_series('DFEDTARU')
    return {
        'effective_fed_funds_rate': dff.get(d),
        'target_lower': low.get(d),
        'target_upper': high.get(d),
    }


def build_payload(now: datetime):
    trade_date, tsp_funds = fetch_tsp_latest(now)
    fed = fetch_fed_for_date(trade_date)
    return {
        'schema_version': 'v1',
        'as_of_utc': now.replace(microsecond=0).isoformat(),
        'trade_date': trade_date,
        'fed': {
            'effective_fed_funds_rate': fed['effective_fed_funds_rate'],
            'target_lower': fed['target_lower'],
            'target_upper': fed['target_upper'],
            'source': [
                'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF',
                'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARL',
                'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU',
            ],
        },
        'tsp': {
            'funds': tsp_funds,
            'source': 'https://www.tspdatacenter.com/daily-share-prices/',
            'note': 'Unofficial mirror used because tsp.gov may block direct server access.',
        },
        'meta': {
            'producer': 'moose-core',
        },
    }


def main():
    now = datetime.now(timezone.utc)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    payload = build_payload(now)
    trade_date = payload['trade_date']

    last = STATE_FILE.read_text().strip() if STATE_FILE.exists() else ''
    changed = trade_date != last

    LATEST_FILE.write_text(json.dumps(payload, indent=2) + '\n')

    if changed:
        snap = SNAP_DIR / f'{trade_date}.json'
        snap.write_text(json.dumps(payload, indent=2) + '\n')
        STATE_FILE.write_text(trade_date + '\n')
        print(f'NEW {trade_date} -> {snap}')
    else:
        print(f'UNCHANGED {trade_date}')


if __name__ == '__main__':
    main()
