#!/usr/bin/env bash
set -euo pipefail

LOG=/home/moose/projects/m2/logs/update_prices.log
mkdir -p /home/moose/projects/m2/logs

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] RUN update_prices" >> "$LOG"
if /usr/bin/flock -n /tmp/m2_prices.lock /usr/bin/python3 /home/moose/projects/m2/repo/src/update_prices.py >> "$LOG" 2>&1; then
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] DONE rc=0" >> "$LOG"
else
  rc=$?
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] DONE rc=${rc}" >> "$LOG"
  exit "$rc"
fi
