from chains.hyperevm import CORE_WRITER
ACTIONS={1:'Limit order',2:'Vault transfer',3:'Token delegate',4:'Staking deposit',5:'Staking withdraw',6:'Spot send',7:'USD class transfer',8:'Finalize EVM Contract',9:'Add API wallet',10:'Cancel order by oid',11:'Cancel order by cloid',12:'Approve builder fee',13:'Send asset',14:'Reflect EVM supply change',15:'Borrow/lend operation'}
def decode_dynamic_bytes(calldata):
    try:
        h=calldata[2:] if calldata.startswith('0x') else calldata
        if len(h)<72:return b''
        body=bytes.fromhex(h[8:]); off=int.from_bytes(body[:32],'big')
        if off+32>len(body):return b''
        n=int.from_bytes(body[off:off+32],'big'); return body[off+32:off+32+n]
    except Exception:return b''
def parse_tx(tx):
    if (tx.get('to') or '').lower()!=CORE_WRITER:return None
    raw=decode_dynamic_bytes(tx.get('input') or '0x')
    if len(raw)<4:return {'kind':'corewriter','action_id':None,'action':'Unknown','version':None}
    version=raw[0]; aid=int.from_bytes(raw[1:4],'big'); return {'kind':'corewriter','version':version,'action_id':aid,'action':ACTIONS.get(aid,f'Action {aid}')}
