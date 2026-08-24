from __future__ import annotations

# HyperEVM native read precompile addresses, aligned with hyper-evm-lib.
SPOT_BALANCE = '0x0000000000000000000000000000000000000801'
L1_BLOCK_NUMBER = '0x0000000000000000000000000000000000000809'
ACCOUNT_MARGIN_SUMMARY = '0x000000000000000000000000000000000000080f'
CORE_USER_EXISTS = '0x0000000000000000000000000000000000000810'

HYPE_TOKEN_INDEX = 150
USDC_TOKEN_INDEX = 0


def _word_uint(v):
    return int(v).to_bytes(32, 'big', signed=False).hex()


def _word_address(addr):
    h = (addr or '').lower().replace('0x', '')
    if len(h) != 40:
        raise ValueError('invalid address')
    return ('0' * 24) + h


def _data(*words):
    return '0x' + ''.join(words)


def _words(result):
    h = (result or '0x')[2:]
    if not h:
        return []
    if len(h) % 64:
        raise ValueError('invalid ABI result length')
    return [h[i:i + 64] for i in range(0, len(h), 64)]


def _u(w):
    return int(w, 16)


def _i(w):
    x = int(w, 16)
    return x - (1 << 256) if x & (1 << 255) else x


class ReadPrecompile:
    """Read-only HyperCore state verification through HyperEVM eth_call.

    HyperEVM read precompiles take raw ABI arguments without a 4-byte selector.
    """

    def __init__(self, rpc):
        self.rpc = rpc

    def _call(self, address, data='0x'):
        return self.rpc.call('eth_call', [{'to': address, 'data': data}, 'latest'], 12)

    def l1_block_number(self):
        ws = _words(self._call(L1_BLOCK_NUMBER))
        return _u(ws[0]) if ws else None

    def core_user_exists(self, user):
        ws = _words(self._call(CORE_USER_EXISTS, _data(_word_address(user))))
        return bool(_u(ws[0])) if ws else False

    def spot_balance(self, user, token_index):
        ws = _words(self._call(SPOT_BALANCE, _data(_word_address(user), _word_uint(token_index))))
        if len(ws) < 3:
            raise ValueError('short spot-balance result')
        return {'total_raw': _u(ws[0]), 'hold_raw': _u(ws[1]), 'entry_ntl_raw': _u(ws[2])}

    def account_margin_summary(self, user, perp_dex_index=0):
        ws = _words(self._call(ACCOUNT_MARGIN_SUMMARY, _data(_word_uint(perp_dex_index), _word_address(user))))
        if len(ws) < 4:
            raise ValueError('short margin-summary result')
        return {
            'account_value_raw': _i(ws[0]),
            'margin_used_raw': _u(ws[1]),
            'ntl_pos_raw': _u(ws[2]),
            'raw_usd_raw': _i(ws[3]),
        }

    def wallet_check(self, user):
        out = {'ok': False, 'user': user}
        try:
            out['l1_block_number'] = self.l1_block_number()
            out['core_user_exists'] = self.core_user_exists(user)
            if out['core_user_exists']:
                out['margin'] = self.account_margin_summary(user)
                out['hype_spot'] = self.spot_balance(user, HYPE_TOKEN_INDEX)
                out['usdc_spot'] = self.spot_balance(user, USDC_TOKEN_INDEX)
            out['ok'] = True
        except Exception as e:
            out['error'] = str(e)[:240]
        return out
