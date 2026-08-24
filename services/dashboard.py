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
                latest=int(store.kv_get('latest_block','0'));hb=int(store.kv_get('scanner_heartbeat','0'));now=int(time.time());return self._json({'version':'0.1.0','ok':bool(hb and now-hb<30),'latest_block':latest,'scanner_age_sec':now-hb if hb else None,'hype_usd':store.kv_get('hype_usd')})
            if self.path=='/api/events':return self._json(store.recent(100))
            if self.path not in ('/','/zh','/en'):self.send_error(404);return
            zh=self.path!='/en';title='HyperEVM Chain Radar · 实时资金监控' if zh else 'HyperEVM Chain Radar · Real-time Capital Monitor';rows=store.recent(30)
            trs=''.join(f"<tr><td>{e['id']}</td><td>{e['kind']}</td><td>{e.get('direction') or ''}</td><td>{e.get('protocol') or ''}</td><td>{('$'+format(e['usd'],',.0f')) if e.get('usd') else ''}</td></tr>" for e in rows)
            html=f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{title}</title><style>body{{font-family:system-ui;background:#071018;color:#dce7ef;margin:24px}}h1{{color:#7cf7c8}}.card{{background:#101c27;padding:16px;border-radius:14px;margin:12px 0}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #243545;text-align:left}}a{{color:#7cf7c8}}</style><h1>{title}</h1><div class=card>Chain ID 999 · HYPE/USD: {store.kv_get('hype_usd','—')} · Block: {store.kv_get('latest_block','—')} · <a href='/api/health'>API Health</a></div><div class=card><table><tr><th>ID</th><th>Event</th><th>Direction</th><th>Protocol</th><th>USD</th></tr>{trs}</table></div>"
            b=html.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    ThreadingHTTPServer((host,int(port)),H).serve_forever()
