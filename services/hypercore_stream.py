from __future__ import annotations
import json,logging,os,time
import websocket
log=logging.getLogger('hypercore-ws')
class HyperCoreStream:
    def __init__(self,store,url='wss://api.hyperliquid.xyz/ws',correlator=None,telegram=None):
        self.store=store;self.url=url;self.correlator=correlator;self.tg=telegram;self.zh=os.getenv('LANGUAGE','zh_CN').lower().startswith('zh')
        self.coins=[x.strip() for x in os.getenv('HYPERCORE_TRADE_COINS','@107').split(',') if x.strip()];self.min_usd=float(os.getenv('HYPERCORE_SMART_MONEY_MIN_USD','100000'));self.whale=float(os.getenv('HYPERCORE_WHALE_TRADE_USD','500000'))
    def _save_trade(self,t):
        try:
            users=t.get('users') or [];px=float(t.get('px') or 0);sz=float(t.get('sz') or 0);usd=px*sz
            if len(users)<2 or usd<self.min_usd:return
            coin=t.get('coin') or '';symbol='HYPE' if coin in ('@107','HYPE') else coin;stamp=int((t.get('time') or int(time.time()*1000))/1000);base=f"{t.get('hash') or 'core'}:{t.get('tid')}"
            for actor,direction in ((users[0],'BUY'),(users[1],'SELL')):
                e={'ts':stamp,'tx_hash':base,'source':'hypercore','kind':'HYPERCORE_TRADE','protocol':'HyperCore Spot','token':coin,'symbol':symbol,'actor':str(actor).lower(),'direction':direction,'usd':usd,'details':{'px':px,'sz':sz,'coin':coin,'tid':t.get('tid'),'hash':t.get('hash')}}
                if self.store.add_event(**e):
                    if self.correlator:self.correlator.observe(e)
                    if self.tg and usd>=self.whale:
                        msg=(f"🐋 HyperCore 大额现货成交\n方向：{direction}\n资产：{symbol}\n金额：${usd:,.0f}\n钱包：{actor}" if self.zh else f"🐋 HyperCore Whale Spot Trade\nSide: {direction}\nAsset: {symbol}\nAmount: ${usd:,.0f}\nWallet: {actor}");self.tg.send(msg)
        except Exception:log.exception('HyperCore trade parse')
    def _message(self,ws,msg):
        try:
            x=json.loads(msg);ch=x.get('channel');data=x.get('data') or {};self.store.kv_set('hypercore_ws_heartbeat',int(time.time()))
            if ch=='allMids':
                mids=data.get('mids') or data
                if isinstance(mids,dict):
                    px=mids.get('HYPE') or mids.get('@107')
                    if px:self.store.kv_set('hype_usd',float(px))
            elif ch=='trades':
                rows=data if isinstance(data,list) else data.get('trades') or []
                for t in rows:self._save_trade(t)
                self.store.kv_set('hypercore_trade_heartbeat',int(time.time()))
        except Exception:log.exception('HyperCore message parse')
    def _open(self,w):
        w.send(json.dumps({'method':'subscribe','subscription':{'type':'allMids'}}))
        for coin in self.coins:w.send(json.dumps({'method':'subscribe','subscription':{'type':'trades','coin':coin}}))
    def run(self,stop):
        while not stop.is_set():
            try:
                ws=websocket.WebSocketApp(self.url,on_message=self._message,on_open=self._open);ws.run_forever(ping_interval=25,ping_timeout=10)
            except Exception:log.exception('HyperCore websocket')
            stop.wait(3)
