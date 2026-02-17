# Moose-Core Data Pipeline

Professional ingest/normalize/publish pipeline for market + macro data.

## Scope (Phase 1)
- Fed Funds effective + target range + FOMC calendar
- TSP funds: C, S, I, G, F
- Publish canonical JSON snapshots for downstream dashboard VPS

## Directory layout
- `config/` source config + JSON schemas
- `src/` pipeline code
- `scripts/` run/deploy/transfer utilities
- `docs/` runbook + data contract
- `tests/` unit/integration tests

Runtime directories (outside git):
- `/home/moose/projects/m2/data`
- `/home/moose/projects/m2/logs`
- `/home/moose/projects/m2/state`

## Quick start
```bash
cd /home/moose/projects/m2/repo
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

## Git bootstrap
```bash
cd /home/moose/projects/m2/repo
git init
git add .
git commit -m "Initial Moose-Core pipeline scaffold"
# then add remote + push
```
