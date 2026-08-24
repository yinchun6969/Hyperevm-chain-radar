CHAIN_ID=999
DEFAULT_RPC='https://rpc.hyperliquid.xyz/evm'
HYPE_SYSTEM='0x2222222222222222222222222222222222222222'
CORE_WRITER='0x3333333333333333333333333333333333333333'
WHYPE='0x5555555555555555555555555555555555555555'
USDC='0xb88339cb7199b77e23db6e890353e22632ba630f'
HYPERSWAP_V3_FACTORY='0xb1c0fa0b789320044a6f623cfe5ebda9562602e3'
READ_PRECOMPILE_START=0x800

def norm(a): return (a or '').lower()
def topic_addr(t):
    if not t:return ''
    h=t[2:] if t.startswith('0x') else t
    return '0x'+h[-40:].lower()
def is_core_system_address(a):
    a=norm(a); return len(a)==42 and a.startswith('0x20')
def classify_block(block):
    g=int(block.get('gasLimit','0x0'),16)
    if g>=20_000_000:return 'big'
    if g and g<=5_000_000:return 'small'
    return 'unknown'
