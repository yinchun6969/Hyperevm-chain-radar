from __future__ import annotations
import time

class CapitalFlowCorrelator:
    def __init__(self,store,telegram,language='zh_CN',window_min=180,p1_usd=100000,p0_transfer_usd=500000,p0_buy_usd=250000,p0_lp_usd=250000):
        self.store=store;self.tg=telegram;self.zh=(language or '').lower().startswith('zh')
        self.window=max(300,int(window_min)*60);self.p1=float(p1_usd);self.p0t=float(p0_transfer_usd);self.p0b=float(p0_buy_usd);self.p0l=float(p0_lp_usd)
    def observe(self,e):
        actor=(e.get('actor') or '').lower();usd=float(e.get('usd') or 0);kind=e.get('kind') or '';direction=e.get('direction') or ''
        if len(actor)!=42:return
        delta={}
        if kind=='HYPERCORE_TRADE':
            delta['core_trade_count']=1;delta['core_buy_usd' if direction=='BUY' else 'core_sell_usd']=usd
        elif kind=='CORE_EVM_TRANSFER':delta['core_to_evm_usd' if direction=='CORE_TO_EVM' else 'evm_to_core_usd']=usd
        elif kind=='SWAP':
            delta['evm_trade_count']=1;delta['evm_buy_usd' if direction.startswith('BUY') else 'evm_sell_usd']=usd
        elif kind=='ADD_LP':delta['lp_add_usd']=usd
        elif kind=='REMOVE_LP':delta['lp_remove_usd']=usd
        if delta:self.store.wallet_flow(actor,e.get('ts'),**delta)
        if kind in ('CORE_EVM_TRANSFER','SWAP','ADD_LP'):self._check_sequence(actor)
    def _check_sequence(self,actor):
        rows=self.store.actor_events(actor,int(time.time())-self.window)
        transfers=[e for e in rows if e['kind']=='CORE_EVM_TRANSFER' and e.get('direction')=='CORE_TO_EVM' and float(e.get('usd') or 0)>=self.p1]
        buys=[e for e in rows if e['kind']=='SWAP' and str(e.get('direction') or '').startswith('BUY') and float(e.get('usd') or 0)>=self.p1]
        lps=[e for e in rows if e['kind']=='ADD_LP' and float(e.get('usd') or 0)>=self.p1]
        if not transfers or not buys or not lps:return
        lp=lps[-1];buy=next((x for x in reversed(buys) if x['ts']<=lp['ts'] and (not lp.get('token') or not x.get('token') or x.get('token')==lp.get('token'))),None)
        if not buy:return
        transfer=next((x for x in reversed(transfers) if x['ts']<=buy['ts']),None)
        if not transfer:return
        t,b,l=(float(transfer.get('usd') or 0),float(buy.get('usd') or 0),float(lp.get('usd') or 0))
        level='P0' if t>=self.p0t and b>=self.p0b and l>=self.p0l else 'P1'
        key='sequence:'+':'.join([actor,str(transfer.get('tx_hash')),str(buy.get('tx_hash')),str(lp.get('tx_hash'))])
        details={'actor':actor,'transfer_usd':t,'buy_usd':b,'lp_usd':l,'transfer_tx':transfer.get('tx_hash'),'buy_tx':buy.get('tx_hash'),'lp_tx':lp.get('tx_hash'),'window_sec':lp['ts']-transfer['ts']}
        if not self.store.claim_alert(key,level,'CORE_EVM_BUY_LP',details):return
        self.store.wallet_flow(actor,sequence_count=1)
        self.store.add_event(ts=int(time.time()),block_number=lp.get('block_number'),tx_hash=lp.get('tx_hash'),source='intelligence',kind='CAPITAL_SEQUENCE',protocol='HyperCore + HyperSwap',token=buy.get('token'),symbol=buy.get('symbol'),actor=actor,pool=lp.get('pool'),direction='CORE_TO_EVM_TO_BUY_TO_LP',usd=t,details=details)
        if self.zh:msg=f"🔥 {level} · Core→EVM→BUY→LP 资金链\n钱包：{actor}\nCore→EVM：${t:,.0f}\nEVM BUY：${b:,.0f}\nLP ADD：${l:,.0f}\n耗时：{details['window_sec']//60} 分钟"
        else:msg=f"🔥 {level} · Core→EVM→BUY→LP Sequence\nWallet: {actor}\nCore→EVM: ${t:,.0f}\nEVM BUY: ${b:,.0f}\nLP ADD: ${l:,.0f}\nElapsed: {details['window_sec']//60} min"
        self.tg.send(msg)
