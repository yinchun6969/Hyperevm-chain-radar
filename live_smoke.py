#!/usr/bin/env python3
from __future__ import annotations
import time
from core.rpc import RPCPool
from chains.hyperevm import CHAIN_ID, DEFAULT_RPC
from services.hypercore_info import HyperCoreInfoClient
from services.read_precompile import ReadPrecompile

ZERO_USER = '0x' + '00' * 20


def retry(label, fn, attempts=3, display=None):
    last = None
    for i in range(attempts):
        try:
            value = fn()
            shown = display(value) if display else 'ok'
            print(f'[OK] {label}: {shown}')
            return value
        except Exception as e:
            last = e
            if i + 1 < attempts:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f'{label} failed after {attempts} attempts: {last}')


def main():
    rpc = RPCPool([DEFAULT_RPC])
    cid = retry('HyperEVM chain id', lambda: int(rpc.call('eth_chainId'), 16), display=str)
    if cid != CHAIN_ID:
        raise RuntimeError(f'wrong chain id {cid}, expected {CHAIN_ID}')
    block = retry('HyperEVM latest block', lambda: int(rpc.call('eth_blockNumber'), 16), display=str)
    if block <= 0:
        raise RuntimeError('invalid HyperEVM block number')

    info = HyperCoreInfoClient(timeout=8)
    mids = retry('HyperCore allMids', info.all_mids, display=lambda x: f'{len(x or {})} mids')
    hype = (mids or {}).get('HYPE') or (mids or {}).get('@107')
    if not hype or float(hype) <= 0:
        raise RuntimeError('HYPE mid not found in HyperCore allMids')
    print(f'[OK] HYPE mid: {hype}')

    perp = retry('HyperCore clearinghouseState', lambda: info.clearinghouse_state(ZERO_USER), display=lambda x: 'marginSummary present' if isinstance(x, dict) and 'marginSummary' in x else 'unexpected shape')
    if not isinstance(perp, dict) or 'marginSummary' not in perp or 'assetPositions' not in perp:
        raise RuntimeError('unexpected clearinghouseState response shape')
    spot = retry('HyperCore spotClearinghouseState', lambda: info.spot_state(ZERO_USER), display=lambda x: 'balances present' if isinstance(x, dict) and 'balances' in x else 'unexpected shape')
    if not isinstance(spot, dict) or 'balances' not in spot:
        raise RuntimeError('unexpected spotClearinghouseState response shape')
    vaults = retry('HyperCore userVaultEquities', lambda: info.vault_equities(ZERO_USER), display=lambda x: f'{len(x or [])} rows')
    if not isinstance(vaults, list):
        raise RuntimeError('unexpected userVaultEquities response shape')

    l1 = retry('HyperEVM L1 block precompile', ReadPrecompile(rpc).l1_block_number, display=str)
    if not l1 or int(l1) <= 0:
        raise RuntimeError('invalid L1 block number from read precompile')
    print('LIVE_SMOKE_OK')


if __name__ == '__main__':
    main()
