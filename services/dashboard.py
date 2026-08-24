from __future__ import annotations
import json,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

def run(store,host='127.0.0.1',port=8788):
    class H(BaseHTTPRequestHandler):
        def log_message(self,*a):return
        def _json(self,obj):
            b=json.dumps(obj,ensure_ascii=False,default=str).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def do_GET(self):
            if self.path=='/api/health':
                latest=int(store.kv_get('latest_block','0'));hb=int(store.kv_get('scanner_heartbeat','0'));wh=int(store.kv_get('hypercore_ws_heartbeat','0'));now=int(time.time())
                return self._json({'version':'0.2.0','ok':bool(hb and now-hb<30),'latest_block':latest,'scanner_age_sec':now-hb if hb else None,'hypercore_ws_age_sec':now-wh if wh else None,'hype_usd':store.kv_get('hype_usd'),'hyperswap_v3_pools':store.pool_count('HyperSwap V3'),'pool_bootstrap_mode':store.kv_get('pool_bootstrap_mode')})
            if self.path=='/api/events':return self._json(store.recent(100))
            if self.path=='/api/wallets':return self._json(store.top_wallets(50))
            if self.path not in ('/','/zh','/en'):self.send_error(404);return
            zh=self.path!='/en';title='HyperEVM Chain Radar · HYPE 资金雷达' if zh else 'HyperEVM Chain Radar · HYPE Capital Radar';rows=store.recent(40);wallets=store.top_wallets(12)
            trs=''.join(f"<tr><td>{e['kind']}</td><td>{e.get('direction') or ''}</td><td>{e.get('protocol') or ''}</td><td>{('$'+format(e['usd'],',.0f')) if e.get('usd') else ''}</td><td>{(e.get('actor') or '')[:10]}</td></tr>" for e in rows)
            wrs=''.join(f"<tr><td>{w['score']}</td><td>{w['address'][:10]}…</td><td>${w['core_to_evm_usd']:,.0f}</td><td>${w['evm_buy_usd']:,.0f}</td><td>${w['lp_add_usd']:,.0f}</td><td>{w['sequence_count']}</td></tr>" for w in wallets)
            html=f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{title}</title><style>body{{font-family:system-ui;background:#071018;color:#dce7ef;margin:24px}}h1,h2{{color:#7cf7c8}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}.card{{background:#101c27;padding:16px;border-radius:14px;margin:12px 0}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:8px;border-bottom:1px solid #243545;text-align:left}}a{{color:#7cf7c8}}</style><h1>{title}</h1><div class=grid><div class=card>HYPE/USD<br><b>{store.kv_get('hype_usd','—')}</b></div><div class=card>Block<br><b>{store.kv_get('latest_block','—')}</b></div><div class=card>HyperSwap V3 Pools<br><b>{store.pool_count('HyperSwap V3')}</b></div><div class=card>Bootstrap<br><b>{store.kv_get('pool_bootstrap_mode','pending')}</b></div></div><div class=card><h2>{'聪明钱地址' if zh else 'Smart-money wallets'}</h2><table><tr><th>Score</th><th>Wallet</th><th>Core→EVM</th><th>EVM BUY</th><th>LP ADD</th><th>Seq</th></tr>{wrs}</table></div><div class=card><h2>{'最近事件' if zh else 'Recent events'}</h2><table><tr><th>Event</th><th>Direction</th><th>Protocol</th><th>USD</th><th>Actor</th></tr>{trs}</table></div><div class=card><a href='/api/health'>Health</a> · <a href='/api/events'>Events API</a> · <a href='/api/wallets'>Wallets API</a></div>"
            b=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    ThreadingHTTPServer((host,int(port)),H).serve_forever()
