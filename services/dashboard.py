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
                latest=int(store.kv_get('latest_block','0'));hb=int(store.kv_get('scanner_heartbeat','0'));wh=int(store.kv_get('hypercore_ws_heartbeat','0'));w360=int(store.kv_get('wallet360_heartbeat','0'));sws=int(store.kv_get('smart_wallet_ws_heartbeat','0'));now=int(time.time())
                return self._json({'version':'0.3.0','ok':bool(hb and now-hb<30),'latest_block':latest,'scanner_age_sec':now-hb if hb else None,'hypercore_ws_age_sec':now-wh if wh else None,'wallet360_age_sec':now-w360 if w360 else None,'smart_wallet_ws_age_sec':now-sws if sws else None,'wallet360_watch_count':int(store.kv_get('wallet360_watch_count','0') or 0),'smart_wallet_stream_count':int(store.kv_get('smart_wallet_stream_count','0') or 0),'hype_usd':store.kv_get('hype_usd'),'hyperswap_v3_pools':store.pool_count('HyperSwap V3'),'pool_bootstrap_mode':store.kv_get('pool_bootstrap_mode')})
            if self.path=='/api/events':return self._json(store.recent(100))
            if self.path=='/api/wallets':return self._json(store.top_wallets(50))
            if self.path=='/api/wallet360':return self._json(store.wallet360_rows(50))
            if self.path.startswith('/api/wallet360/'):
                address=self.path.rsplit('/',1)[-1].lower();row=store.wallet360_get(address)
                if not row:self.send_error(404);return
                try:row['snapshot']=json.loads(row.get('snapshot') or '{}')
                except Exception:pass
                return self._json(row)
            if self.path not in ('/','/zh','/en'):self.send_error(404);return
            zh=self.path!='/en';title='HyperEVM Chain Radar · Wallet 360' if zh else 'HyperEVM Chain Radar · Wallet 360';rows=store.recent(40);wallets=store.top_wallets(12);full=store.wallet360_rows(12)
            trs=''.join(f"<tr><td>{e['kind']}</td><td>{e.get('direction') or ''}</td><td>{e.get('protocol') or ''}</td><td>{('$'+format(e['usd'],',.0f')) if e.get('usd') else ''}</td><td>{(e.get('actor') or '')[:10]}</td></tr>" for e in rows)
            wrs=''.join(f"<tr><td>{w['score']}</td><td>{w['address'][:10]}…</td><td>${w['core_to_evm_usd']:,.0f}</td><td>${w['evm_buy_usd']:,.0f}</td><td>${w['lp_add_usd']:,.0f}</td><td>{w['sequence_count']}</td></tr>" for w in wallets)
            frs=''.join(f"<tr><td>{w['score']}</td><td>{w['address'][:10]}…</td><td>${w['account_value']:,.0f}</td><td>${w['perp_ntl']:,.0f}</td><td>{w['largest_perp_coin'] or ''} ${w['largest_perp_usd']:,.0f}</td><td>{w['hype_spot']:,.2f}</td><td>${w['vault_equity']:,.0f}</td><td>{'✓' if w['precompile_ok'] else '—'}</td></tr>" for w in full)
            html=f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{title}</title><style>body{{font-family:system-ui;background:#071018;color:#dce7ef;margin:24px}}h1,h2{{color:#7cf7c8}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}.card{{background:#101c27;padding:16px;border-radius:14px;margin:12px 0;overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:8px;border-bottom:1px solid #243545;text-align:left;white-space:nowrap}}a{{color:#7cf7c8}}</style><h1>{title}</h1><div class=grid><div class=card>HYPE/USD<br><b>{store.kv_get('hype_usd','—')}</b></div><div class=card>Block<br><b>{store.kv_get('latest_block','—')}</b></div><div class=card>HyperSwap V3 Pools<br><b>{store.pool_count('HyperSwap V3')}</b></div><div class=card>Wallet 360<br><b>{store.kv_get('wallet360_watch_count','0')}</b></div></div><div class=card><h2>{'Wallet 360 状态' if zh else 'Wallet 360 state'}</h2><table><tr><th>Score</th><th>Wallet</th><th>Account</th><th>Perp Ntl</th><th>Largest</th><th>HYPE</th><th>Vault</th><th>Precompile</th></tr>{frs}</table></div><div class=card><h2>{'聪明钱资金历史' if zh else 'Smart-money flow history'}</h2><table><tr><th>Score</th><th>Wallet</th><th>Core→EVM</th><th>EVM BUY</th><th>LP ADD</th><th>Seq</th></tr>{wrs}</table></div><div class=card><h2>{'最近事件' if zh else 'Recent events'}</h2><table><tr><th>Event</th><th>Direction</th><th>Protocol</th><th>USD</th><th>Actor</th></tr>{trs}</table></div><div class=card><a href='/api/health'>Health</a> · <a href='/api/events'>Events</a> · <a href='/api/wallets'>Wallets</a> · <a href='/api/wallet360'>Wallet 360 API</a></div>"
            b=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    ThreadingHTTPServer((host,int(port)),H).serve_forever()
