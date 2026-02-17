#!/usr/bin/env bash
set -euo pipefail

/usr/bin/flock -n /tmp/m2_prices.lock \
  /usr/bin/python3 /home/moose/projects/m2/repo/src/update_prices.py \
  >> /home/moose/projects/m2/logs/update_prices.log 2>&1
