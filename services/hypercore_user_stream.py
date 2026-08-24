from __future__ import annotations
import json
import logging
import os
import threading
import time

import websocket

log = logging.getLogger('hypercore-user-ws')


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _event_ms(v):
    x = _f(v)
    if x <= 0:
        return int(time.time() * 1000)
    return int(x if x > 10_000_000_000 else x * 1000)


def _ledger_usd(delta):
    """Return an explicitly USD/USDC-denominated amount when available.

    Generic `amount` is deliberately not treated as USD because it may be HYPE
    or another spot token.
    """
    for key in ('netWithdrawnUsd', 'usdcValue', 'liquidatedNtlPos', 'requestedUsd', 'usdc'):
        value = abs(_f((delta or {}).get(key)))
        if value:
            return value
    return 0.0


class HyperCoreUserStream:
    """Continuous per-user HyperCore streams for the highest-scoring wallets.

    The watchlist is updated on the live socket with subscribe/unsubscribe, so a
    periodic watchlist refresh does not intentionally create a monitoring gap.
    On an unexpected reconnect, only a small recent slice of snapshot data is
    accepted and normal event dedupe prevents re-alerting already stored events.
    """

    def __init__(self, store, telegram=None, url='wss://api.hyperliquid.xyz/ws'):
        self.store = store
        self.tg = telegram
        self.url = url
        self.zh = os.getenv('LANGUAGE', 'zh_CN').lower().startswith('zh')
        self.min_score = int(os.getenv('SMART_WALLET_STREAM_MIN_SCORE', '70'))
        self.max_wallets = max(1, int(os.getenv('SMART_WALLET_STREAM_MAX_WALLETS', '8')))
        self.rebuild = max(60, int(os.getenv('SMART_WALLET_STREAM_REBUILD_SEC', '300')))
        self.fill_alert = float(os.getenv('SMART_WALLET_FILL_ALERT_USD', '250000'))
        self.snapshot_recovery_ms = max(0, int(os.getenv('SMART_WALLET_SNAPSHOT_RECOVERY_SEC', '5'))) * 1000
        self.scores = {}
        self.stop = None
        self._ws = None
        self._active = set()
        self._lock = threading.RLock()
        self._last_event_ms = int(time.time() * 1000)

    def _watch(self):
        rows = self.store.wallet_candidates(self.min_score, self.max_wallets)
        self.scores = {x['address']: int(x.get('score') or 0) for x in rows}
        return list(self.scores)

    def _remember_time(self, item):
        self._last_event_ms = max(self._last_event_ms, _event_ms((item or {}).get('time')))

    def _snapshot_recent(self, item):
        return _event_ms((item or {}).get('time')) >= self._last_event_ms - self.snapshot_recovery_ms

    def _save_fill(self, user, fill):
        px = _f(fill.get('px'))
        sz = _f(fill.get('sz'))
        usd = abs(px * sz)
        side = str(fill.get('side') or '').upper()
        direction = 'BUY' if side in ('B', 'BUY') else 'SELL' if side in ('A', 'S', 'SELL') else str(fill.get('dir') or side or 'FILL')
        event_ms = _event_ms(fill.get('time'))
        stamp = event_ms // 1000
        coin = str(fill.get('coin') or '')
        tid = fill.get('tid')
        # One taker order may generate multiple fills with the same hash/oid/time.
        # HyperCore tid is the per-trade identity and must be part of dedupe.
        part = str(tid) if tid is not None else f"{fill.get('px')}:{fill.get('sz')}:{fill.get('dir') or ''}"
        tx = f"{fill.get('hash') or 'core'}:{fill.get('oid')}:{fill.get('time')}:{part}"
        event = {
            'ts': stamp,
            'tx_hash': tx,
            'source': 'hypercore-user',
            'kind': 'HYPERCORE_USER_FILL',
            'protocol': 'HyperCore',
            'token': coin,
            'symbol': coin,
            'actor': user,
            'direction': direction,
            'usd': usd,
            'details': fill,
        }
        inserted = self.store.add_event(**event)
        self._remember_time(fill)
        if inserted:
            self.store.wallet_flow(user, stamp)
            score = self.scores.get(user, 0)
            if self.tg and usd >= self.fill_alert:
                msg = (
                    f"⚡ 高分钱包 HyperCore 成交\nScore：{score}\n钱包：{user}\n方向：{direction}\n资产：{coin}\n金额：${usd:,.0f}"
                    if self.zh
                    else f"⚡ Smart Wallet HyperCore Fill\nScore: {score}\nWallet: {user}\nSide: {direction}\nAsset: {coin}\nAmount: ${usd:,.0f}"
                )
                self.tg.send(msg)

    def _save_ledger(self, user, row):
        delta = (row or {}).get('delta') or {}
        kind = str(delta.get('type') or 'ledger')
        event_ms = _event_ms((row or {}).get('time'))
        stamp = event_ms // 1000
        usd = _ledger_usd(delta)
        detail_id = ':'.join(str(delta.get(k) or '') for k in ('token', 'destination', 'amount', 'usdcValue', 'usdc'))
        tx = f"{(row or {}).get('hash') or 'ledger'}:{kind}:{(row or {}).get('time')}:{detail_id}"
        event = {
            'ts': stamp,
            'tx_hash': tx,
            'source': 'hypercore-user',
            'kind': 'HYPERCORE_LEDGER',
            'protocol': 'HyperCore',
            'actor': user,
            'direction': kind.upper(),
            'usd': usd or None,
            'details': delta,
        }
        inserted = self.store.add_event(**event)
        self._remember_time(row)
        if inserted:
            self.store.wallet_flow(user, stamp)

    def _message(self, ws, msg):
        try:
            payload = json.loads(msg)
            channel = payload.get('channel')
            data = payload.get('data') or {}
            self.store.kv_set('smart_wallet_ws_heartbeat', int(time.time()))
            if not isinstance(data, dict):
                return
            user = str(data.get('user') or '').lower()
            if len(user) != 42:
                return
            is_snapshot = bool(data.get('isSnapshot'))
            if channel == 'userFills':
                rows = data.get('fills') or []
                for fill in rows:
                    if not is_snapshot or self._snapshot_recent(fill):
                        self._save_fill(user, fill)
            elif channel == 'userNonFundingLedgerUpdates':
                rows = data.get('nonFundingLedgerUpdates') or []
                for row in rows:
                    if not is_snapshot or self._snapshot_recent(row):
                        self._save_ledger(user, row)
        except Exception:
            log.exception('smart-wallet WS parse')

    @staticmethod
    def _sub_message(method, kind, user):
        return json.dumps({'method': method, 'subscription': {'type': kind, 'user': user}})

    def _sync_subscriptions(self, ws):
        desired = set(self._watch())
        with self._lock:
            if self._ws is not ws:
                return
            remove = self._active - desired
            add = desired - self._active
            for user in sorted(remove):
                ws.send(self._sub_message('unsubscribe', 'userFills', user))
                ws.send(self._sub_message('unsubscribe', 'userNonFundingLedgerUpdates', user))
                self._active.discard(user)
            for user in sorted(add):
                ws.send(self._sub_message('subscribe', 'userFills', user))
                ws.send(self._sub_message('subscribe', 'userNonFundingLedgerUpdates', user))
                self._active.add(user)
            self.store.kv_set('smart_wallet_stream_count', len(self._active))

    def _sync_loop(self, ws):
        while self.stop and not self.stop.wait(self.rebuild):
            with self._lock:
                if self._ws is not ws:
                    return
            try:
                self._sync_subscriptions(ws)
            except Exception:
                log.exception('smart-wallet subscription sync')
                return

    def _open(self, ws):
        with self._lock:
            self._ws = ws
            self._active = set()
        now = int(time.time())
        self.store.kv_set('smart_wallet_ws_heartbeat', now)
        self.store.kv_set('smart_wallet_ws_connected', 1)
        self._sync_subscriptions(ws)
        threading.Thread(target=self._sync_loop, args=(ws,), name='smart-wallet-sync', daemon=True).start()

    def _close(self, ws, code, msg):
        with self._lock:
            if self._ws is ws:
                self._ws = None
                self._active = set()
        self.store.kv_set('smart_wallet_ws_connected', 0)
        self.store.kv_set('smart_wallet_stream_count', 0)

    def run(self, stop):
        self.stop = stop
        while not stop.is_set():
            if not self._watch():
                self.store.kv_set('smart_wallet_ws_connected', 0)
                self.store.kv_set('smart_wallet_stream_count', 0)
                stop.wait(30)
                continue
            try:
                ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._message,
                    on_open=self._open,
                    on_close=self._close,
                )
                ws.run_forever(ping_interval=25, ping_timeout=10)
            except Exception:
                log.exception('smart-wallet websocket')
            finally:
                with self._lock:
                    self._ws = None
                    self._active = set()
                self.store.kv_set('smart_wallet_ws_connected', 0)
                self.store.kv_set('smart_wallet_stream_count', 0)
            stop.wait(3)
