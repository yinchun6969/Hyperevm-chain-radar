from __future__ import annotations
import json,logging,time
import websocket
log=logging.getLogger('hypercore-ws')
class HyperCoreStream:
    def __init__(self,store,url='wss://api.hyperliquid.xyz/ws'):self.store=store;self.url=url
    def _message(self,ws,msg):
        try:
            x=json.loads(msg)
            if x.get('channel')=='allMids':
                data=x.get('data') or {}; mids=data.get('mids') or data
                if isinstance(mids,dict):
                    px=mids.get('HYPE') or mids.get('@107')
                    if px:self.store.kv_set('hype_usd',float(px));self.store.kv_set('hypercore_ws_heartbeat',int(time.time()))
        except Exception:log.exception('HyperCore message parse')
    def run(self,stop):
        while not stop.is_set():
            try:
                ws=websocket.WebSocketApp(self.url,on_message=self._message,on_open=lambda w:w.send(json.dumps({'method':'subscribe','subscription':{'type':'allMids'}})))
                ws.run_forever(ping_interval=25,ping_timeout=10)
            except Exception:log.exception('HyperCore websocket')
            stop.wait(3)
