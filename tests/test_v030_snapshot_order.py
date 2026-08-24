import json
import os
import tempfile
import time
import unittest

from core.storage import Store
from services.hypercore_user_stream import HyperCoreUserStream


class TG:
    def send(self, text):
        pass


class SnapshotOrderRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.store = Store(self.tmp.name)

    def tearDown(self):
        try:
            self.store.db.close()
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_newest_first_snapshot_uses_one_fixed_cutoff(self):
        addr = '0x' + 'ab' * 20
        stream = HyperCoreUserStream(self.store, TG())
        stream.scores = {addr: 90}
        stream.snapshot_recovery_ms = 5000
        now_ms = int(time.time() * 1000)
        stream._last_event_ms = now_ms

        # Both fills belong to the same 5-second recovery overlap, but the
        # snapshot is intentionally newest-first. Processing the first row must
        # not move the cutoff forward and incorrectly drop the second row.
        newer = {
            'coin': 'HYPE', 'px': '80', 'sz': '10', 'side': 'B',
            'time': now_ms + 2000, 'hash': '0xnewer', 'oid': 9, 'tid': 9002,
        }
        older = {
            'coin': 'HYPE', 'px': '80', 'sz': '11', 'side': 'B',
            'time': now_ms - 4000, 'hash': '0xolder', 'oid': 9, 'tid': 9001,
        }
        msg = {
            'channel': 'userFills',
            'data': {'isSnapshot': True, 'user': addr, 'fills': [newer, older]},
        }
        stream._message(None, json.dumps(msg))

        rows = [e for e in self.store.recent(10) if e['kind'] == 'HYPERCORE_USER_FILL']
        self.assertEqual(len(rows), 2)
        hashes = {e['tx_hash'].split(':', 1)[0] for e in rows}
        self.assertEqual(hashes, {'0xnewer', '0xolder'})


if __name__ == '__main__':
    unittest.main()
