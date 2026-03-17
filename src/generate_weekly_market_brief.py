#!/usr/bin/env python3
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = Path('/home/moose/projects/m2')
OUT_DIR = BASE / 'briefs'
UA = {'User-Agent': 'Mozilla/5.0'}


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8', 'ignore'))


def get_text(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')


def parse_market_cap(v: str) -> float:
    if not v:
        return 0.0
    s = v.replace('$', '').replace(',', '').strip().upper()
    m = re.match(r'([0-9.]+)\s*([MBT]?)', s)
    if not m:
        return 0.0
    n = float(m.group(1))
    unit = m.group(2)
    mult = {'': 1, 'M': 1e6, 'B': 1e9, 'T': 1e12}.get(unit, 1)
    return n * mult


def week_bounds(today: date):
    # upcoming Monday-Sunday week window
    days_to_monday = (7 - today.weekday()) % 7
    if days_to_monday == 0:
        days_to_monday = 7
    monday = today + timedelta(days=days_to_monday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def fetch_earnings_for_day(d: date):
    url = f'https://api.nasdaq.com/api/calendar/earnings?date={d.isoformat()}'
    data = get_json(url)
    rows = ((data.get('data') or {}).get('rows') or [])
    out = []
    for r in rows:
        out.append({
            'date': d.isoformat(),
            'time': r.get('time') or 'N/A',
            'symbol': r.get('symbol') or '',
            'name': r.get('name') or '',
            'marketCap': r.get('marketCap') or '',
            'epsForecast': r.get('epsForecast') or '',
        })
    return out


def fetch_fomc_2026_dates():
    html = get_text('https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm')
    # Parse only 2026 block
    m = re.search(r'2026 FOMC Meetings(.*?)2025 FOMC Meetings', html, re.S)
    block = m.group(1) if m else ''
    pairs = re.findall(r'<strong>([A-Za-z/]+)</strong>\s*</div>\s*<div[^>]*>([^<]+)</div>', block)

    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
        'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12,
    }
    out = []
    for month_name, date_range in pairs:
        month_name = month_name.strip()
        date_range = date_range.strip().replace('*', '')
        if month_name not in month_map:
            continue
        mth = month_map[month_name]
        # take first day for week overlap detection
        first_day_match = re.match(r'(\d+)', date_range)
        if not first_day_match:
            continue
        day = int(first_day_match.group(1))
        try:
            d = date(2026, mth, day)
            out.append({'month': month_name, 'date_range': date_range, 'first_day': d.isoformat()})
        except Exception:
            continue
    return out


def fetch_whitehouse_recent(limit=8):
    xml_text = get_text('https://www.whitehouse.gov/briefings-statements/feed/')
    root = ET.fromstring(xml_text)
    channel = root.find('channel')
    items = []
    if channel is None:
        return items
    for item in channel.findall('item')[:limit]:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        items.append({'title': title, 'link': link, 'pubDate': pub})
    return items


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date()
    monday, sunday = week_bounds(today)

    earnings = []
    cur = monday
    while cur <= sunday:
        if cur.weekday() < 5:  # market weekdays
            try:
                earnings.extend(fetch_earnings_for_day(cur))
            except Exception:
                pass
        cur += timedelta(days=1)

    top_earnings = sorted(earnings, key=lambda r: parse_market_cap(r.get('marketCap', '')), reverse=True)[:25]

    fomc = fetch_fomc_2026_dates()
    fomc_week = [m for m in fomc if monday.isoformat() <= m['first_day'] <= sunday.isoformat()]

    wh = fetch_whitehouse_recent(limit=12)

    md = []
    md.append(f"# Weekly Market Intel Brief ({monday.isoformat()} to {sunday.isoformat()})")
    md.append('')
    md.append(f"Generated (UTC): {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}")
    md.append('')
    md.append('## 1) High-Priority This Week')
    if fomc_week:
        md.append('- **FOMC Meeting Week:** Yes')
        for f in fomc_week:
            md.append(f"  - {f['month']} {f['date_range']}")
    else:
        md.append('- **FOMC Meeting Week:** No scheduled 2026 FOMC dates in this window')
    md.append(f"- **Top scheduled earnings tracked:** {len(top_earnings)} (by market cap from Nasdaq calendar)")
    md.append('')

    md.append('## 2) Earnings Watchlist (Top by Market Cap)')
    md.append('| Date | Time | Symbol | Company | Market Cap | EPS Forecast |')
    md.append('|---|---|---|---|---:|---:|')
    for r in top_earnings:
        md.append(f"| {r['date']} | {r['time']} | {r['symbol']} | {r['name']} | {r['marketCap']} | {r['epsForecast']} |")
    if not top_earnings:
        md.append('| N/A | N/A | N/A | No earnings data available | - | - |')
    md.append('')

    md.append('## 3) Fed / Policy Calendar')
    if fomc_week:
        md.append('- FOMC in-range this week (see above).')
    else:
        md.append('- No in-range FOMC meeting dates this week.')
    md.append('')

    md.append('## 4) Presidential / White House Announcements (Recent)')
    for item in wh[:8]:
        md.append(f"- {item['pubDate']} — [{item['title']}]({item['link']})")
    if not wh:
        md.append('- No feed items parsed.')
    md.append('')

    md.append('## 5) Major Business Deals (M&A)')
    md.append('- **Status:** Not yet integrated into a reliable structured source in this pipeline.')
    md.append('- **Planned:** add Reuters/Bloomberg-equivalent feed source or SEC 8-K deal-event parser adapter.')
    md.append('')

    md.append('## Sources')
    md.append('- Nasdaq earnings calendar API: `https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD`')
    md.append('- Federal Reserve FOMC calendars: `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`')
    md.append('- White House briefings feed: `https://www.whitehouse.gov/briefings-statements/feed/`')

    out_path = OUT_DIR / f'weekly-market-intel-{monday.isoformat()}.md'
    out_path.write_text('\n'.join(md) + '\n')
    print(out_path)


if __name__ == '__main__':
    main()
