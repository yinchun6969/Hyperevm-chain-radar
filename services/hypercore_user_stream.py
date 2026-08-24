from __future__ import annotations
import json,logging,os,threading,time
import websocket

log=logging.getLogger('hypercore-user-ws')


def _f(v):
    try:return float(v or 0)
    except (TypeError,ValueError):return 0.0


class HyperCoreUserStream:
    """Dynamic WebSocket subscriptions for the highest-scoring wallets.

    Subscription snapshots are ignored to avoid replaying historical fills when
    the watch list is periodically rebuilt.
    """
    def __init__(self,store,telegram=None,url='wss://api.hyperliquid.xyz/ws'):
        self.store=store;self.tg=telegram;self.url=url;self.zh=os.getenv('LANGUAGE','zh_CN').lower().startswith('zh')
        self.min_score=int(os.getenv('SMART_WALLET_STREAM_MIN_SCORE','70'));self.max_wallets=max(1,int(os.getenv('SMART_WALLET_STREAM_MAX_WALLETS','8')))
        self.rebuild=max(180,int(os.getenv('SMART_WALLET_STREAM_REBUILD_SEC','300')));self.fill_alert=float(os.getenv('SMART_WALLET_FILL_ALERT_USD','250000'));self.scores={};self.stop=None
    def _watch(self):
        rows=self.store.wallet_candidates(self.min_score,self.max_wallets);self.scores={x['address']:int(x.get('score') or 0) for x in rows};return list(self.scores)
    def _save_fill(self,user,f):
        px=_f(f.get('px'));sz=_f(f.get('sz'));usd=abs(px*sz);side=str(f.get('side') or '').upper();direction='BUY' if side in ('B','BUY') else 'SELL' if side in ('A','S','SELL') else str(f.get('dir') or side or 'FILL')
        stamp=int(_f(f.get('time'))/1000) if _f(f.get('time'))>10_000_000_000 else int(_f(f.get('time')) or time.time());coin=str(f.get('coin') or '')
        tx=f"{f.get('hash') or 'core'}:{f.get('oid')}:{f.get('time')}"
        e={'ts':stamp,'tx_hash':tx,'source':'hypercore-user','kind':'HYPERCORE_USER_FILL','protocol':'HyperCore','token':coin,'symbol':coin,'actor':user,'direction':direction,'usd':usd,'details':f}
        if self.store.add_event(**e):
            self.store.wallet_flow(user,stamp)
            score=self.scores.get(user,0)
            if self.tg and usd>=self.fill_alert:
                msg=(f"⚡ 高分钱包 HyperCore 成交\nScore：{score}\n钱包：{user}\n方向：{direction}\n资产：{coin}\n金额：${usd:,.0f}" if self.zh else f"⚡ Smart Wallet HyperCore Fill\nScore: {score}\nWallet: {user}\nSide: {direction}\nAsset: {coin}\nAmount: ${usd:,.0f}");self.tg.send(msg)
    def _save_ledger(self,user,row):
        delta=(row or {}).get('delta') or {};kind=str(delta.get('type') or 'ledger');stamp=int(_f((row or {}).get('time'))/1000) if _f((row or {}).get('time'))>10_000_000_000 else int(_f((row or {}).get('time')) or time.time());usd=abs(_f(delta.get('usdc')));tx=f"{(row or {}).get('hash') or 'ledger'}:{kind}:{(row or {}).get('time')}"
        e={'ts':stamp,'tx_hash':tx,'source':'hypercore-user','kind':'HYPERCORE_LEDGER','protocol':'HyperCore','actor':user,'direction':kind.upper(),'usd':usd or None,'details':delta}
        if self.store.add_event(**e):self.store.wallet_flow(user,stamp)
    def _message(self,ws,msg):
        try:
            x=json.loads(msg);ch=x.get('channel');data=x.get('data') or {};self.store.kv_set('smart_wallet_ws_heartbeat',int(time.time()))
            if not isinstance(data,dict):return
            if data.get('isSnapshot'):return
            user=str(data.get('user') or '').lower()
            if len(user)!=42:return
            if ch=='userFills':
                for f in data.get('fills') or []:self._save_fill(user,f)
            elif ch=='userNonFundingLedgerUpdates':
                rows=data.get('nonFundingLedgerUpdates') or data.get('ledgerUpdates') or data.get('updates') or []
                for row in rows:self._save_ledger(user,row)
        except Exception:log.exception('smart-wallet WS parse')
    def _close_later(self,ws):
        if self.stop and not self.stop.wait(self.rebuild):
            try:ws.close()
            except Exception:pass
    def _open(self,ws):
        wallets=self._watch();self.store.kv_set('smart_wallet_stream_count',len(wallets))
        for user in wallets:
            ws.send(json.dumps({'method':'subscribe','subscription':{'type':'userFills','user':user}}))
            ws.send(json.dumps({'method':'subscribe','subscription':{'type':'userNonFundingLedgerUpdates','user':user}}))
        threading.Thread(target=self._close_later,args=(ws,),daemon=True).start()
    def run(self,stop):
        self.stop=stop
        while not stop.is_set():
            if not self._watch():stop.wait(30);continue
            try:
                ws=websocket.WebSocketApp(self.url,on_message=self._message,on_open=self._open);ws.run_forever(ping_interval=25,ping_timeout=10)
            except Exception:log.exception('smart-wallet websocket')
            stop.wait(3)
