from __future__ import annotations
import json,time
class LPRugRadar:
    def __init__(self,store,telegram,abs_usd=1_000_000,p0_pct=50,p1_pct=30,baseline_min=500_000,cooldown=900,language='zh_CN'):
        self.s=store;self.tg=telegram;self.abs=float(abs_usd);self.p0=float(p0_pct);self.p1=float(p1_pct);self.base=float(baseline_min);self.cool=int(cooldown);self.zh=language.lower().startswith('zh')
    def on_lp(self,pool,kind,usd,token='',symbol=''):
        if not usd or usd<=0:return None
        with self.s.lock:
            r=self.s.db.execute('SELECT observed_add_usd,observed_remove_usd,observed_net_usd FROM lp_state WHERE pool=?',(pool,)).fetchone() or (0,0,0);add,rem,net=map(float,r);baseline=net;pct=None
            if kind=='ADD_LP':add+=usd;net+=usd
            elif kind=='REMOVE_LP':
                if baseline>=self.base:pct=usd/baseline*100
                rem+=usd;net-=usd
            self.s.db.execute('INSERT OR REPLACE INTO lp_state VALUES(?,?,?,?,?)',(pool,add,rem,net,int(time.time())));self.s.db.commit()
            if kind!='REMOVE_LP':return None
            level='P0' if usd>=self.abs or (pct is not None and pct>=self.p0) else 'P1' if usd>=self.abs*.5 or (pct is not None and pct>=self.p1) else None
            if not level:return None
            key=f'lp:{pool}';old=self.s.db.execute('SELECT ts,level FROM alerts WHERE alert_key=?',(key,)).fetchone();now=int(time.time())
            if old and now-int(old[0])<self.cool and not (level=='P0' and old[1]!='P0'):return None
            details={'pool':pool,'usd':usd,'observed_drain_pct':pct,'token':token,'symbol':symbol};self.s.db.execute('INSERT OR REPLACE INTO alerts VALUES(?,?,?,?,?)',(key,now,level,'lp_rug',json.dumps(details)));self.s.db.commit()
        ratio='—' if pct is None else f'{pct:.1f}%';text=(f'🔴 {level} · HyperEVM LP 大规模撤出\n代币：{symbol or token or "UNKNOWN"}\n本次撤池：${usd:,.0f}\n观察基线撤出：{ratio}\n池：{pool}\n说明：比例基于 Radar 已观察流量，不等于精确 TVL。' if self.zh else f'🔴 {level} · HyperEVM Large LP Withdrawal\nToken: {symbol or token or "UNKNOWN"}\nRemoval: ${usd:,.0f}\nObserved-flow drain: {ratio}\nPool: {pool}\nNote: observed-flow ratio is not exact TVL.')
        self.tg.send(text);return level
