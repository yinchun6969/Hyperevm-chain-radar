#!/usr/bin/env python3
import os,sys,sqlite3,requests
from pathlib import Path
from core.env import load_dotenv
load_dotenv()
from core.rpc import RPCPool
from chains.hyperevm import DEFAULT_RPC,CHAIN_ID
def main():
    rows=[];add=lambda s,n,d='':rows.append((s,n,str(d)));add('OK' if sys.version_info>=(3,10) else 'FAIL','Python',sys.version.split()[0]);urls=[os.getenv('HYPEREVM_RPC_URL',DEFAULT_RPC)]+[x.strip() for x in os.getenv('HYPEREVM_RPC_URLS','').split(',') if x.strip()]
    try:
        p=RPCPool(urls);cid=int(p.call('eth_chainId'),16);block=int(p.call('eth_blockNumber'),16);add('OK' if cid==CHAIN_ID else 'FAIL','HyperEVM RPC',f'chain={cid} block={block} active={p.label(p.urls[p.active])}');add('OK' if len(p.urls)>1 else 'WARN','RPC redundancy',f'{len(p.urls)} endpoint(s)')
    except Exception as e:add('FAIL','HyperEVM RPC',e)
    db=Path(os.getenv('DB_PATH',Path(__file__).with_name('radar.db')))
    try:d=sqlite3.connect(db);x=d.execute('PRAGMA integrity_check').fetchone()[0];add('OK' if x=='ok' else 'FAIL','SQLite',x);d.close()
    except Exception as e:add('WARN','SQLite',e)
    try:r=requests.get(f"http://127.0.0.1:{os.getenv('DASHBOARD_PORT','8788')}/api/health",timeout=2);add('OK' if r.ok else 'WARN','Dashboard',r.status_code)
    except Exception:add('WARN','Dashboard','not running')
    print('HyperEVM Chain Radar Doctor V0.1.0');print('='*56)
    for s,n,d in rows:print(f'[{s}] {n}: {d}')
    print('='*56);fail=any(s=='FAIL' for s,_,_ in rows);print('STATUS:','FAIL' if fail else 'HEALTHY/WARN');raise SystemExit(1 if fail else 0)
if __name__=='__main__':main()
