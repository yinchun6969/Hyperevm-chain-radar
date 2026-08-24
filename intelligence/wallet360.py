from __future__ import annotations
import json,logging,os,time

log=logging.getLogger('wallet360')


def _f(v,default=0.0):
    try:return float(v)
    except (TypeError,ValueError):return float(default)


def summarize_perp(state):
    state=state or {};m=state.get('marginSummary') or {};positions=[];pnl=0.0;largest={'coin':'','usd':0.0}
    for row in state.get('assetPositions') or []:
        p=(row or {}).get('position') or {};usd=abs(_f(p.get('positionValue')));pnl+=_f(p.get('unrealizedPnl'))
        if usd>0:positions.append(p)
        if usd>largest['usd']:largest={'coin':str(p.get('coin') or ''),'usd':usd,'szi':p.get('szi'),'entry_px':p.get('entryPx'),'unrealized_pnl':_f(p.get('unrealizedPnl')),'leverage':p.get('leverage')}
    return {'account_value':_f(m.get('accountValue')),'ntl_pos':_f(m.get('totalNtlPos')),'margin_used':_f(m.get('totalMarginUsed')),'raw_usd':_f(m.get('totalRawUsd')),'withdrawable':_f(state.get('withdrawable')),'unrealized_pnl':pnl,'positions':len(positions),'largest':largest,'open_positions':positions[:20]}


def summarize_spot(state):
    balances=[];hype=0.0;usdc=0.0
    for b in (state or {}).get('balances') or []:
        coin=str((b or {}).get('coin') or '');total=_f((b or {}).get('total'));hold=_f((b or {}).get('hold'))
        if abs(total)>0:balances.append({'coin':coin,'total':total,'hold':hold,'token':(b or {}).get('token')})
        if coin.upper()=='HYPE':hype=total
        elif coin.upper()=='USDC':usdc=total
    balances.sort(key=lambda x:abs(x['total']),reverse=True)
    return {'hype':hype,'usdc':usdc,'assets':len(balances),'balances':balances[:30]}


def summarize_vaults(rows):
    out=[];total=0.0
    for x in rows or []:
        eq=_f((x or {}).get('equity'));total+=eq
        if eq:out.append({'vault':(x or {}).get('vaultAddress'),'equity':eq,'locked_until':(x or {}).get('lockedUntilTimestamp')})
    out.sort(key=lambda x:x['equity'],reverse=True)
    return total,out[:20]


class Wallet360Service:
    def __init__(self,store,info,precompile=None,telegram=None):
        self.store=store;self.info=info;self.precompile=precompile;self.tg=telegram;self.zh=os.getenv('LANGUAGE','zh_CN').lower().startswith('zh')
        self.min_score=int(os.getenv('WALLET360_MIN_SCORE','60'));self.max_wallets=max(1,int(os.getenv('WALLET360_MAX_WALLETS','12')))
        self.refresh=max(30,int(os.getenv('WALLET360_REFRESH_SEC','60')));self.vault_refresh=max(120,int(os.getenv('WALLET360_VAULT_REFRESH_SEC','300')))
        self.pc_refresh=max(180,int(os.getenv('READ_PRECOMPILE_REFRESH_SEC','300')));self.pc_max=max(0,int(os.getenv('READ_PRECOMPILE_MAX_WALLETS','3')))
        self.state_alert=float(os.getenv('WALLET360_STATE_ALERT_USD','1000000'));self._vault={};self._pc={}
    def candidates(self):return self.store.wallet_candidates(self.min_score,self.max_wallets)
    def _vault_state(self,address,now):
        old=self._vault.get(address)
        if old and now-old[0]<self.vault_refresh:return old[1],old[2]
        try:total,rows=summarize_vaults(self.info.vault_equities(address));self._vault[address]=(now,total,rows);return total,rows
        except Exception as e:
            log.warning('vault snapshot failed wallet=%s err=%s',address,str(e)[:180]);return (old[1],old[2]) if old else (0.0,[])
    def _precompile_state(self,address,now,rank):
        old=self._pc.get(address)
        if rank>=self.pc_max or not self.precompile:return old[1] if old else {'ok':False,'skipped':True}
        if old and now-old[0]<self.pc_refresh:return old[1]
        result=self.precompile.wallet_check(address);self._pc[address]=(now,result);return result
    def _maybe_state_alert(self,address,score,old,snap):
        if not old or self.state_alert<=0:return
        try:prev=json.loads(old.get('snapshot') or '{}')
        except Exception:prev={}
        before=(prev.get('perp') or {}).get('ntl_pos') or 0;after=(snap.get('perp') or {}).get('ntl_pos') or 0;delta=abs(float(after)-float(before))
        if delta<self.state_alert:return
        bucket=int(time.time())//3600;key=f'wallet360:{address}:{bucket}'
        details={'address':address,'score':score,'before_ntl':before,'after_ntl':after,'delta_ntl':delta}
        if not self.store.claim_alert(key,'P1','WALLET360_STATE_CHANGE',details):return
        self.store.add_event(ts=int(time.time()),source='intelligence',kind='WALLET360_STATE_CHANGE',protocol='HyperCore',actor=address,direction='PERP_EXPOSURE_CHANGE',usd=delta,details=details)
        if self.tg:
            msg=(f"🐋 P1 · 高分钱包仓位变化\n钱包：{address}\nScore：{score}\nPerp 名义仓位变化：${delta:,.0f}\n当前名义仓位：${float(after):,.0f}" if self.zh else f"🐋 P1 · Smart Wallet Position Change\nWallet: {address}\nScore: {score}\nPerp notional change: ${delta:,.0f}\nCurrent notional: ${float(after):,.0f}");self.tg.send(msg)
    def refresh_wallet(self,row,rank=0):
        address=row['address'];now=int(time.time());old=self.store.wallet360_get(address)
        perp=summarize_perp(self.info.clearinghouse_state(address));spot=summarize_spot(self.info.spot_state(address));vault_total,vaults=self._vault_state(address,now);pc=self._precompile_state(address,now,rank)
        snap={'address':address,'score':int(row.get('score') or 0),'updated_at':now,'perp':perp,'spot':spot,'vault_equity':vault_total,'vaults':vaults,'precompile':pc,'tags':row.get('tags')}
        self._maybe_state_alert(address,snap['score'],old,snap);self.store.save_wallet360(address,snap['score'],snap);return snap
    def run_once(self):
        rows=self.candidates();self.store.kv_set('wallet360_watch_count',len(rows));ok=0
        for rank,row in enumerate(rows):
            try:self.refresh_wallet(row,rank);ok+=1
            except Exception as e:log.warning('wallet360 failed wallet=%s err=%s',row.get('address'),str(e)[:200])
        self.store.kv_set('wallet360_heartbeat',int(time.time()));self.store.kv_set('wallet360_last_ok',ok);return ok
    def run(self,stop):
        while not stop.is_set():
            started=time.time();self.run_once();stop.wait(max(1,self.refresh-int(time.time()-started)))
