#!/usr/bin/env python3
from __future__ import annotations
import time
from core.rpc import RPCPool
from chains.hyperevm import CHAIN_ID, DEFAULT_RPC
from services.hypercore_info import HyperCoreInfoClient
from services.read_precompile import ReadPrecompile


def retry(label, fn, attempts=3):
    last = None
    for i in range(attempts):
        try:
            value = fn()
            print(f'[OK] {label}: {value}')
            return value
        except Exception as e:
            last = e
            if i + 1 < attempts:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f'{label} failed after {attempts} attempts: {last}')


def main():
    rpc = RPCPool([DEFAULT_RPC])
    cid = retry('HyperEVM chain id', lambda: int(rpc.call('eth_chainId'), 16))
    if cid != CHAIN_ID:
        raise RuntimeError(f'wrong chain id {cid}, expected {CHAIN_ID}')
    block = retry('HyperEVM latest block', lambda: int(rpc.call('eth_blockNumber'), 16))
    if block <= 0:
        raise RuntimeError('invalid HyperEVM block number')

    info = HyperCoreInfoClient(timeout=8)
    mids = retry('HyperCore allMids', info.all_mids)
    hype = (mids or {}).get('HYPE') or (mids or {}).get('@107')
    if not hype or float(hype) <= 0:
        raise RuntimeError('HYPE mid not found in HyperCore allMids')
    print(f'[OK] HYPE mid: {hype}')

    l1 = retry('HyperEVM L1 block precompile', ReadPrecompile(rpc).l1_block_number)
    if not l1 or int(l1) <= 0:
        raise RuntimeError('invalid L1 block number from read precompile')
    print('LIVE_SMOKE_OK')


if __name__ == '__main__':
    main()
