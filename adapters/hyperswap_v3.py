from core.keccak import topic
from chains.hyperevm import topic_addr,HYPERSWAP_V3_FACTORY
POOL_CREATED=topic('PoolCreated(address,address,uint24,int24,address)')
SWAP=topic('Swap(address,address,int256,int256,uint160,uint128,int24)')
MINT=topic('Mint(address,address,int24,int24,uint128,uint256,uint256)')
BURN=topic('Burn(address,int24,int24,uint128,uint256,uint256)')
ACTIVITY={SWAP.lower():'SWAP',MINT.lower():'ADD_LP',BURN.lower():'REMOVE_LP'}
def _words(data):
    h=data[2:] if data.startswith('0x') else data
    return [h[i:i+64] for i in range(0,len(h),64) if len(h[i:i+64])==64]
def _uint(w):return int(w,16)
def _int(w):
    x=int(w,16); return x-(1<<256) if x&(1<<255) else x
def parse_pool_created(log):
    t=log.get('topics') or []
    if (log.get('address') or '').lower()!=HYPERSWAP_V3_FACTORY or len(t)<4 or t[0].lower()!=POOL_CREATED.lower():return None
    ws=_words(log.get('data') or '0x')
    if len(ws)<2:return None
    return {'token0':topic_addr(t[1]),'token1':topic_addr(t[2]),'fee':int(t[3],16),'tick_spacing':_int(ws[0]),'pool':'0x'+ws[1][-40:]}
def parse_activity(log):
    t=log.get('topics') or []
    if not t:return None
    kind=ACTIVITY.get(t[0].lower())
    if not kind:return None
    ws=_words(log.get('data') or '0x')
    if kind=='SWAP':return {'kind':kind,'amount0':_int(ws[0]),'amount1':_int(ws[1])} if len(ws)>=2 else None
    if kind=='ADD_LP':return {'kind':kind,'amount0':_uint(ws[-2]),'amount1':_uint(ws[-1])} if len(ws)>=4 else None
    return {'kind':kind,'amount0':_uint(ws[-2]),'amount1':_uint(ws[-1])} if len(ws)>=3 else None
