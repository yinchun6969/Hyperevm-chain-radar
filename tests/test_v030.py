import json
import os
import tempfile
import time
import unittest

from core.storage import Store
from intelligence.wallet360 import Wallet360Service, summarize_perp, summarize_spot, summarize_vaults
from services.hypercore_user_stream import HyperCoreUserStream, _ledger_usd
from services.read_precompile import ReadPrecompile, _word_address, _word_uint


def word(v):
    return hex(int(v) % (1 << 256))[2:].rjust(64, '0')


class FakeRPC:
    def call(self, method, params, timeout=0):
        to = params[0]['to'].lower()
        if to.endswith('0809'):
            return '0x' + word(123456)
        if to.endswith('0810'):
            return '0x' + word(1)
        if to.endswith('080f'):
            # Official AccountMarginSummary order:
            # accountValue, marginUsed, ntlPos, rawUsd.
            return '0x' + word(-5) + word(7) + word(9) + word(-11)
        if to.endswith('0801'):
            token = int(params[0]['data'][-64:], 16)
            return '0x' + word(150000000 if token == 150 else 250000000) + word(0) + word(0)
        raise AssertionError(to)


class FakeInfo:
    def clearinghouse_state(self, user):
        return {
            'marginSummary': {
                'accountValue': '2500000',
                'totalNtlPos': '4000000',
                'totalMarginUsed': '800000',
                'totalRawUsd': '100000',
            },
            'withdrawable': '500000',
            'assetPositions': [
                {'position': {'coin': 'BTC', 'positionValue': '3000000', 'unrealizedPnl': '120000', 'szi': '2', 'entryPx': '100000', 'leverage': {'type': 'cross', 'value': 5}}},
                {'position': {'coin': 'ETH', 'positionValue': '1000000', 'unrealizedPnl': '-20000', 'szi': '10', 'entryPx': '4000', 'leverage': {'type': 'cross', 'value': 3}}},
            ],
        }

    def spot_state(self, user):
        return {'balances': [{'coin': 'HYPE', 'token': 150, 'total': '123.5', 'hold': '2'}, {'coin': 'USDC', 'token': 0, 'total': '4567', 'hold': '0'}]}

    def vault_equities(self, user):
        return [{'vaultAddress': '0x' + 'aa' * 20, 'equity': '750000', 'lockedUntilTimestamp': 0}]


class FakePC:
    def wallet_check(self, user):
        return {'ok': True, 'user': user, 'l1_block_number': 999, 'core_user_exists': True}


class FakeWS:
    def __init__(self):
        self.sent = []
        self.close_count = 0

    def send(self, payload):
        self.sent.append(json.loads(payload))

    def close(self):
        self.close_count += 1


class TG:
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)


class V030(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.s = Store(self.tmp.name)

    def tearDown(self):
        try:
            self.s.db.close()
            os.unlink(self.tmp.name)
        except Exception:
            pass

    def test_raw_abi_helpers(self):
        addr = '0x' + '12' * 20
        self.assertEqual(len(_word_address(addr)), 64)
        self.assertTrue(_word_address(addr).endswith('12' * 20))
        self.assertEqual(_word_uint(150), word(150))

    def test_read_precompile_decode_official_field_order(self):
        r = ReadPrecompile(FakeRPC())
        self.assertEqual(r.l1_block_number(), 123456)
        self.assertTrue(r.core_user_exists('0x' + '11' * 20))
        margin = r.account_margin_summary('0x' + '11' * 20)
        self.assertEqual(margin['account_value_raw'], -5)
        self.assertEqual(margin['margin_used_raw'], 7)
        self.assertEqual(margin['ntl_pos_raw'], 9)
        self.assertEqual(margin['raw_usd_raw'], -11)
        self.assertEqual(r.spot_balance('0x' + '11' * 20, 150)['total_raw'], 150000000)

    def test_summary_parsers(self):
        info = FakeInfo()
        perp = summarize_perp(info.clearinghouse_state('x'))
        self.assertEqual(perp['positions'], 2)
        self.assertEqual(perp['largest']['coin'], 'BTC')
        self.assertEqual(perp['unrealized_pnl'], 100000)
        spot = summarize_spot(info.spot_state('x'))
        self.assertEqual(spot['hype'], 123.5)
        self.assertEqual(spot['usdc'], 4567)
        equity, rows = summarize_vaults(info.vault_equities('x'))
        self.assertEqual(equity, 750000)
        self.assertEqual(len(rows), 1)

    def test_wallet360_persistence(self):
        addr = '0x' + '44' * 20
        self.s.wallet_flow(addr, core_to_evm_usd=600000, core_buy_usd=600000, evm_buy_usd=600000, lp_add_usd=300000)
        keys = ['WALLET360_MIN_SCORE', 'WALLET360_MAX_WALLETS', 'READ_PRECOMPILE_MAX_WALLETS', 'WALLET360_STATE_ALERT_USD']
        old = {k: os.environ.get(k) for k in keys}
        os.environ['WALLET360_MIN_SCORE'] = '60'
        os.environ['WALLET360_MAX_WALLETS'] = '2'
        os.environ['READ_PRECOMPILE_MAX_WALLETS'] = '1'
        os.environ['WALLET360_STATE_ALERT_USD'] = '0'
        try:
            svc = Wallet360Service(self.s, FakeInfo(), FakePC(), TG())
            self.assertEqual(svc.run_once(), 1)
            row = self.s.wallet360_get(addr)
            self.assertIsNotNone(row)
            self.assertEqual(row['perp_positions'], 2)
            self.assertEqual(row['largest_perp_coin'], 'BTC')
            self.assertEqual(row['precompile_ok'], 1)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_snapshot_recovery_is_bounded(self):
        addr = '0x' + '55' * 20
        stream = HyperCoreUserStream(self.s, TG())
        stream.scores = {addr: 90}
        now_ms = int(time.time() * 1000)
        stream._last_event_ms = now_ms
        old = {'coin': 'HYPE', 'px': '50', 'sz': '10', 'side': 'B', 'time': now_ms - 60000, 'hash': '0xold', 'oid': 1, 'tid': 1}
        recent = {'coin': 'HYPE', 'px': '50', 'sz': '11', 'side': 'B', 'time': now_ms - 1000, 'hash': '0xrecent', 'oid': 1, 'tid': 2}
        msg = {'channel': 'userFills', 'data': {'isSnapshot': True, 'user': addr, 'fills': [old, recent]}}
        stream._message(None, json.dumps(msg))
        fills = [e for e in self.s.recent(10) if e['kind'] == 'HYPERCORE_USER_FILL']
        self.assertEqual(len(fills), 1)
        self.assertIn('0xrecent', fills[0]['tx_hash'])

    def test_fill_tid_prevents_partial_fill_collision(self):
        addr = '0x' + '56' * 20
        stream = HyperCoreUserStream(self.s, TG())
        stream.scores = {addr: 90}
        now_ms = int(time.time() * 1000)
        base = {'coin': 'HYPE', 'px': '50', 'sz': '100', 'side': 'B', 'time': now_ms, 'hash': '0xsame', 'oid': 77}
        fills = [dict(base, tid=1001), dict(base, tid=1002)]
        stream._message(None, json.dumps({'channel': 'userFills', 'data': {'user': addr, 'isSnapshot': False, 'fills': fills}}))
        rows = [e for e in self.s.recent(10) if e['kind'] == 'HYPERCORE_USER_FILL']
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['tx_hash'], rows[1]['tx_hash'])

    def test_official_ledger_field_and_usd_value(self):
        addr = '0x' + '66' * 20
        stream = HyperCoreUserStream(self.s, TG())
        stream.scores = {addr: 90}
        msg = {
            'channel': 'userNonFundingLedgerUpdates',
            'data': {
                'user': addr,
                'isSnapshot': False,
                'nonFundingLedgerUpdates': [{
                    'time': int(time.time() * 1000),
                    'hash': '0xabc',
                    'delta': {'type': 'spotTransfer', 'token': 'HYPE', 'amount': '100', 'usdcValue': '12345', 'user': addr, 'destination': '0x' + '77' * 20, 'fee': '0', 'nativeTokenFee': '0', 'nonce': 1, 'feeToken': 'HYPE'},
                }],
            },
        }
        stream._message(None, json.dumps(msg))
        rows = [e for e in self.s.recent(10) if e['kind'] == 'HYPERCORE_LEDGER']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['usd'], 12345)
        self.assertEqual(_ledger_usd({'type': 'vaultWithdraw', 'netWithdrawnUsd': '9000', 'requestedUsd': '10000'}), 9000)

    def test_ws_open_sets_heartbeat_and_subscribes(self):
        addr = '0x' + '88' * 20
        self.s.wallet_flow(addr, core_to_evm_usd=600000, core_buy_usd=600000, evm_buy_usd=600000, lp_add_usd=300000)
        stream = HyperCoreUserStream(self.s, TG())
        ws = FakeWS()
        stream._open(ws)
        self.assertEqual(self.s.kv_get('smart_wallet_ws_connected'), '1')
        self.assertGreater(int(self.s.kv_get('smart_wallet_ws_heartbeat', '0')), 0)
        types = [x['subscription']['type'] for x in ws.sent]
        self.assertIn('userFills', types)
        self.assertIn('userNonFundingLedgerUpdates', types)
        self.assertEqual(ws.close_count, 0)

    def test_watchlist_sync_does_not_close_socket(self):
        old_addr = '0x' + '91' * 20
        new_addr = '0x' + '92' * 20
        stream = HyperCoreUserStream(self.s, TG())
        ws = FakeWS()
        stream._ws = ws
        stream._active = {old_addr}
        stream._watch = lambda: [new_addr]
        stream._sync_subscriptions(ws)
        methods = [(x['method'], x['subscription']['type'], x['subscription']['user']) for x in ws.sent]
        self.assertIn(('unsubscribe', 'userFills', old_addr), methods)
        self.assertIn(('subscribe', 'userFills', new_addr), methods)
        self.assertEqual(stream._active, {new_addr})
        self.assertEqual(ws.close_count, 0)


if __name__ == '__main__':
    unittest.main()
