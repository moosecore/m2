import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.append('/home/moose/projects/m2/repo/src')
import update_prices as up


class TestUpdatePrices(unittest.TestCase):
    def test_month_year_candidates_wraps_january(self):
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        self.assertEqual(up._month_year_candidates(now), [(1, 2026), (12, 2025)])

    def test_cached_fed_fallback_from_latest(self):
        with tempfile.TemporaryDirectory() as td:
            latest = Path(td) / 'latest.json'
            latest.write_text(json.dumps({
                'fed': {
                    'effective_fed_funds_rate': 4.1,
                    'target_lower': 4.0,
                    'target_upper': 4.25,
                }
            }))
            with patch.object(up, 'LATEST_FILE', latest):
                fb = up._cached_fed_fallback()
                self.assertIsNotNone(fb)
                self.assertEqual(fb['effective_fed_funds_rate'], 4.1)
                self.assertEqual(fb['target_lower'], 4.0)
                self.assertEqual(fb['target_upper'], 4.25)

    def test_fetch_fed_for_date_uses_cache_on_failure(self):
        with tempfile.TemporaryDirectory() as td:
            latest = Path(td) / 'latest.json'
            latest.write_text(json.dumps({
                'fed': {
                    'effective_fed_funds_rate': 3.9,
                    'target_lower': 3.75,
                    'target_upper': 4.0,
                }
            }))
            with patch.object(up, 'LATEST_FILE', latest), \
                 patch.object(up, 'fred_series', side_effect=RuntimeError('network fail')):
                fed = up.fetch_fed_for_date('2026-03-10')
                self.assertEqual(fed['effective_fed_funds_rate'], 3.9)
                self.assertEqual(fed['target_lower'], 3.75)
                self.assertEqual(fed['target_upper'], 4.0)
                self.assertIn('cached_fallback', fed['source_mode'])

    def test_build_payload_shape(self):
        now = datetime(2026, 3, 17, tzinfo=timezone.utc)
        with patch.object(up, 'fetch_tsp_latest', return_value=('2026-03-16', {'C': 1, 'S': 2, 'I': 3, 'G': 4, 'F': 5})), \
             patch.object(up, 'fetch_fed_for_date', return_value={'effective_fed_funds_rate': 4.0, 'target_lower': 3.75, 'target_upper': 4.0, 'source_mode': 'live'}):
            payload = up.build_payload(now)
            self.assertEqual(payload['trade_date'], '2026-03-16')
            self.assertEqual(payload['schema_version'], 'v1')
            self.assertEqual(payload['tsp']['funds']['C'], 1)
            self.assertEqual(payload['fed']['target_upper'], 4.0)

    def test_health_state_cached_counter_and_alert_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            snap_dir = data_dir / 'snapshots'
            snap_dir.mkdir(parents=True, exist_ok=True)

            latest = data_dir / 'latest.json'
            state_file = data_dir / 'last_published_date.txt'
            health_file = data_dir / 'pipeline_health.json'

            cached_fed = {
                'effective_fed_funds_rate': 3.9,
                'target_lower': 3.75,
                'target_upper': 4.0,
                'source_mode': 'cached_fallback (test)'
            }

            with patch.object(up, 'DATA_DIR', data_dir), \
                 patch.object(up, 'SNAP_DIR', snap_dir), \
                 patch.object(up, 'LATEST_FILE', latest), \
                 patch.object(up, 'STATE_FILE', state_file), \
                 patch.object(up, 'HEALTH_FILE', health_file), \
                 patch.object(up, 'fetch_tsp_latest', return_value=('2026-03-16', {'C': 1, 'S': 2, 'I': 3, 'G': 4, 'F': 5})), \
                 patch.object(up, 'fetch_fed_for_date', return_value=cached_fed):

                up.main()
                up.main()
                up.main()

            payload = json.loads(latest.read_text())
            health = json.loads(health_file.read_text())
            self.assertEqual(health['consecutive_cached_fed_runs'], 3)
            self.assertIn('alerts', payload)
            self.assertTrue(any('3+ consecutive runs' in a for a in payload['alerts']))


if __name__ == '__main__':
    unittest.main()
