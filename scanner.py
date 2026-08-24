#!/usr/bin/env python3
from __future__ import annotations
import logging,os,time
from core.env import load_dotenv
load_dotenv()
from core.rpc import RPCPool
from core.storage import Store
from chains.hyperevm import *
from adapters import core_transfers,corewriter,hyperswap_v3
from intelligence.lp_rug import LPRugRadar
from intelligence.capital_flow import CapitalFlowCorrelator
from services.telegram import Telegram

log=logging.getLogger('scanner')
def _hex(n):return hex(int(n))
def _decode_symbol(result):
    if not result or result=='0x':return ''
    try:
        h=result[2:]
        if len(h)==64:return bytes.fromhex(h).rstrip(b'\0').decode('utf-8','ignore')
        b=bytes.fromhex(h);off=int.from_bytes(b[:32],'big');n=int.from_bytes(b[off:off+32],'big');return b[off+32:off+32+n].decode('utf-8','ignore')
    except Exception:return ''

class Scanner:
    def __init__(self):
        urls=[os.getenv('HYPEREVM_RPC_URL',DEFAULT_RPC)]+[x.strip() for x in os.getenv('HYPEREVM_RPC_URLS','').split(',') if x.strip()]
        self.rpc=RPCPool(urls,int(os.getenv('RPC_FAILBACK_SEC','300')));self.store=Store(os.getenv('DB_PATH',str(__import__('pathlib').Path(__file__).with_name('radar.db'))));self.tg=Telegram(os.getenv('TELEGRAM_BOT_TOKEN',''),os.getenv('TELEGRAM_CHAT_ID',''))
        self.zh=os.getenv('LANGUAGE','zh_CN').lower().startswith('zh');self.backfill=int(os.getenv('START_BACKFILL_BLOCKS','20'));self.poll=float(os.getenv('POLL_SECONDS','1'));self.alert=float(os.getenv('ALERT_USD','250000'));self.meta={}
        self.rug=LPRugRadar(self.store,self.tg,float(os.getenv('LP_RUG_ABSOLUTE_USD','1000000')),float(os.getenv('LP_RUG_P0_DRAIN_PCT','50')),float(os.getenv('LP_RUG_P1_DRAIN_PCT','30')),float(os.getenv('LP_RUG_BASELINE_MIN_USD','500000')),int(os.getenv('LP_RUG_COOLDOWN_MIN','15'))*60,os.getenv('LANGUAGE','zh_CN'))
        self.correlator=CapitalFlowCorrelator(self.store,self.tg,os.getenv('LANGUAGE','zh_CN'),int(os.getenv('CAPITAL_SEQUENCE_WINDOW_MIN','180')),float(os.getenv('CAPITAL_SEQUENCE_P1_USD','100000')),float(os.getenv('CAPITAL_SEQUENCE_P0_TRANSFER_USD','500000')),float(os.getenv('CAPITAL_SEQUENCE_P0_BUY_USD','250000')),float(os.getenv('CAPITAL_SEQUENCE_P0_LP_USD','250000')))
    def call(self,m,p=None,t=20):return self.rpc.call(m,p or [],t)
    def token_meta(self,a):
        a=a.lower()
        if a in self.meta:return self.meta[a]
        dec=18;sym=''
        try:dec=int(self.call('eth_call',[{'to':a,'data':'0x313ce567'},'latest']),16)
        except Exception:pass
        try:sym=_decode_symbol(self.call('eth_call',[{'to':a,'data':'0x95d89b41'},'latest']))
        except Exception:pass
        self.meta[a]=(sym,dec);return sym,dec
    def price(self,a):
        a=a.lower()
        if a==USDC:return 1.0
        if a==WHYPE:return float(self.store.kv_get('hype_usd','0') or 0)
        return 0.0
    def amount_usd(self,a,raw):
        sym,dec=self.token_meta(a);px=self.price(a);return (abs(raw)/(10**dec)*px if px else None),sym
    def _alert_event(self,e):
        usd=e.get('usd')
        if not usd or usd<self.alert:return
        if self.zh:text=f"🚨 HyperEVM 资金事件\n类型：{e['kind']}\n方向：{e.get('direction') or '—'}\n协议：{e.get('protocol') or '—'}\n金额：${usd:,.0f}\n代币：{e.get('symbol') or e.get('token') or '—'}\n地址：{e.get('actor') or '—'}"
        else:text=f"🚨 HyperEVM Capital Event\nType: {e['kind']}\nDirection: {e.get('direction') or '—'}\nProtocol: {e.get('protocol') or '—'}\nAmount: ${usd:,.0f}\nToken: {e.get('symbol') or e.get('token') or '—'}\nAddress: {e.get('actor') or '—'}"
        self.tg.send(text)
    def _save(self,**e):
        if self.store.add_event(**e):self._alert_event(e);self.correlator.observe(e)
    def process_core_transfer(self,logx,block):
        x=core_transfers.parse(logx)
        if not x:return
        token=x['token'];usd=None;sym=token
        if token=='HYPE':usd=x['raw']/1e18*float(self.store.kv_get('hype_usd','0') or 0);sym='HYPE';token=HYPE_SYSTEM
        else:usd,sym=self.amount_usd(token,x['raw'])
        self._save(ts=int(time.time()),block_number=block,tx_hash=logx.get('transactionHash'),source='hyperevm',kind='CORE_EVM_TRANSFER',protocol='HyperCore',token=token,symbol=sym,actor=x.get('actor'),direction=x['direction'],usd=usd,details=x)
    def process_pool_created(self,l,b):
        x=hyperswap_v3.parse_pool_created(l)
        if not x:return
        self.store.add_pool(x['pool'],'HyperSwap V3',x['token0'],x['token1'],x['fee'],b,l.get('transactionHash'));s0,_=self.token_meta(x['token0']);s1,_=self.token_meta(x['token1'])
        self._save(ts=int(time.time()),block_number=b,tx_hash=l.get('transactionHash'),source='hyperevm',kind='NEW_POOL',protocol='HyperSwap V3',token=x['pool'],symbol=f'{s0 or x["token0"][:8]}/{s1 or x["token1"][:8]}',pool=x['pool'],details=x)
    def _focus(self,t0,t1,x,s0,s1):
        base={WHYPE,USDC}
        if t0 in base and t1 not in base:return t1,s1,x['amount1']
        if t1 in base and t0 not in base:return t0,s0,x['amount0']
        return t0,s0,x['amount0']
    def process_pool_activity(self,l,b,tx_actor=None):
        x=hyperswap_v3.parse_activity(l)
        if not x:return
        pool=(l.get('address') or '').lower();r=self.store.db.execute('SELECT token0,token1 FROM pools WHERE address=?',(pool,)).fetchone()
        if not r:return
        t0,t1=r;u0,s0=self.amount_usd(t0,x['amount0']);u1,s1=self.amount_usd(t1,x['amount1']);vals=[v for v in (u0,u1) if v is not None];usd=sum(vals) if len(vals)==2 else (vals[0] if vals else None)
        target,target_sym,target_raw=self._focus(t0,t1,x,s0,s1);kind=x['kind'];direction=None
        if kind=='SWAP':direction='BUY' if target_raw<0 else 'SELL' if target_raw>0 else 'SWAP'
        topics=l.get('topics') or [];topic_actor=topic_addr(topics[1]) if len(topics)>1 else None;actor=(tx_actor or topic_actor or '').lower() or None
        details=dict(x);details.update({'token0':t0,'token1':t1,'focus_token':target,'tx_actor':tx_actor})
        self._save(ts=int(time.time()),block_number=b,tx_hash=l.get('transactionHash'),source='hyperevm',kind=kind,protocol='HyperSwap V3',token=target,symbol=target_sym or target[:8],actor=actor,pool=pool,direction=direction,usd=usd,details=details)
        if kind in ('ADD_LP','REMOVE_LP'):self.rug.on_lp(pool,kind,usd or 0,target,target_sym)
    def process_tx(self,tx,b):
        cw=corewriter.parse_tx(tx)
        if cw:self._save(ts=int(time.time()),block_number=b,tx_hash=tx.get('hash'),source='hyperevm',kind='COREWRITER',protocol='HyperCore',actor=(tx.get('from') or '').lower(),direction='EVM_TO_CORE_ACTION',details=cw)
        if (tx.get('from') or '').lower()==HYPE_SYSTEM and (tx.get('to') or '').lower()!=HYPE_SYSTEM:
            raw=int(tx.get('value','0x0'),16);px=float(self.store.kv_get('hype_usd','0') or 0);self._save(ts=int(time.time()),block_number=b,tx_hash=tx.get('hash'),source='hyperevm',kind='CORE_EVM_TRANSFER',protocol='HyperCore',token=HYPE_SYSTEM,symbol='HYPE',actor=(tx.get('to') or '').lower(),direction='CORE_TO_EVM',usd=raw/1e18*px if px else None,details={'raw':raw,'confidence':'best_effort_system_tx'})
    def scan_block(self,b):
        block=self.call('eth_getBlockByNumber',[_hex(b),True],20) or {};self.store.kv_set('block_type',classify_block(block));txs=block.get('transactions') or [];tx_from={(x.get('hash') or '').lower():(x.get('from') or '').lower() for x in txs}
        for tx in txs:self.process_tx(tx,b)
        logs=self.call('eth_getLogs',[{'fromBlock':_hex(b),'toBlock':_hex(b),'topics':[[core_transfers.TRANSFER,core_transfers.RECEIVED,hyperswap_v3.POOL_CREATED]]}],30) or []
        for l in logs:self.process_core_transfer(l,b);self.process_pool_created(l,b)
        pools=self.store.pools('HyperSwap V3')
        if pools:
            for i in range(0,len(pools),100):
                try:
                    ls=self.call('eth_getLogs',[{'fromBlock':_hex(b),'toBlock':_hex(b),'address':pools[i:i+100],'topics':[[hyperswap_v3.SWAP,hyperswap_v3.MINT,hyperswap_v3.BURN]]}],30) or []
                    for l in ls:self.process_pool_activity(l,b,tx_from.get((l.get('transactionHash') or '').lower()))
                except Exception:log.exception('pool activity logs block=%s',b)
        self.store.kv_set('latest_block',b);self.store.kv_set('scanner_heartbeat',int(time.time()))
    def run(self,stop):
        chain=int(self.call('eth_chainId'),16)
        if chain!=CHAIN_ID:raise RuntimeError(f'wrong chain id {chain}, expected {CHAIN_ID}')
        latest=int(self.call('eth_blockNumber'),16);last=int(self.store.kv_get('scanner_cursor','0') or 0)
        if not last:last=max(0,latest-self.backfill)
        while not stop.is_set():
            try:
                tip=int(self.call('eth_blockNumber'),16)
                while last<tip and not stop.is_set():last+=1;self.scan_block(last);self.store.kv_set('scanner_cursor',last)
                stop.wait(self.poll)
            except Exception:log.exception('scanner loop');stop.wait(2)
