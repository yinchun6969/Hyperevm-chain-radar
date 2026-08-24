from __future__ import annotations
import time
import requests


class HyperCoreInfoClient:
    """Small read-only wrapper around Hyperliquid's /info endpoint.

    The caller controls cadence. The client deliberately does not retry in a
    tight loop because HyperCore info requests have weighted IP rate limits.
    """

    def __init__(self, url='https://api.hyperliquid.xyz/info', timeout=8, min_interval=0.08):
        self.url = url
        self.timeout = float(timeout)
        self.min_interval = max(0.0, float(min_interval))
        self.session = requests.Session()
        self._last_call = 0.0

    def post(self, payload):
        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        r = self.session.post(self.url, json=payload, timeout=self.timeout)
        self._last_call = time.monotonic()
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get('error'):
            raise RuntimeError(str(data.get('error')))
        return data

    def clearinghouse_state(self, user):
        return self.post({'type': 'clearinghouseState', 'user': user})

    def spot_state(self, user):
        return self.post({'type': 'spotClearinghouseState', 'user': user})

    def vault_equities(self, user):
        return self.post({'type': 'userVaultEquities', 'user': user})

    def all_mids(self):
        return self.post({'type': 'allMids'})
