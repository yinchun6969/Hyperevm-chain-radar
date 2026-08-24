#!/usr/bin/env python3
import os,sys,sqlite3,requests
from pathlib import Path
from core.env import load_dotenv
load_dotenv()
from core.rpc import RPCPool
from chains.hyperevm import DEFAULT_RPC,CHAIN_ID
from services.hypercore_info import HyperCoreInfoClient
from services.read_precompile import ReadPrecompile

def main():
    rows=[];add=lambda s,n,d='':rows.append((s,n,str(d)));add('OK' if sys.version_info>=(3,10) else 'FAIL','Python',sys.version.split()[0]);urls=[os.getenv('HYPEREVM_RPC_URL',DEFAULT_RPC)]+[x.strip() for x in os.getenv('HYPEREVM_RPC_URLS','').split(',') if x.strip()];p=None
    try:
        p=RPCPool(urls);cid=int(p.call('eth_chainId'),16);block=int(p.call('eth_blockNumber'),16);add('OK' if cid==CHAIN_ID else 'FAIL','HyperEVM RPC',f'chain={cid} block={block} active={p.label(p.urls[p.active])}');add('OK' if len(p.urls)>1 else 'WARN','RPC redundancy',f'{len(p.urls)} endpoint(s)')
    except Exception as e:add('FAIL','HyperEVM RPC',e)
    if p:
        try:l1=ReadPrecompile(p).l1_block_number();add('OK','Read precompile',f'L1 block={l1}')
        except Exception as e:add('WARN','Read precompile',e)
    try:
        info=HyperCoreInfoClient(os.getenv('HYPERCORE_INFO_URL','https://api.hyperliquid.xyz/info'),float(os.getenv('HYPERCORE_INFO_TIMEOUT','8')));mids=info.all_mids();hype=(mids or {}).get('HYPE') or (mids or {}).get('@107');add('OK' if hype else 'WARN','HyperCore Info API',f'HYPE={hype or "not found"}')
    except Exception as e:add('WARN','HyperCore Info API',e)
    db=Path(os.getenv('DB_PATH',Path(__file__).with_name('radar.db')))
    try:
        d=sqlite3.connect(db);x=d.execute('PRAGMA integrity_check').fetchone()[0];tables={r[0] for r in d.execute("SELECT name FROM sqlite_master WHERE type='table'")};pools=d.execute("SELECT COUNT(*) FROM pools WHERE protocol='HyperSwap V3'").fetchone()[0] if 'pools' in tables else 0;wallets=d.execute('SELECT COUNT(*) FROM wallet_profiles').fetchone()[0] if 'wallet_profiles' in tables else 0;w360=d.execute('SELECT COUNT(*) FROM wallet360').fetchone()[0] if 'wallet360' in tables else 0;add('OK' if x=='ok' else 'FAIL','SQLite',f'{x}; pools={pools}; wallets={wallets}; wallet360={w360}');add('OK' if 'wallet360' in tables else 'WARN','Wallet 360 schema','ready' if 'wallet360' in tables else 'start V0.3.0 once to migrate');d.close()
    except Exception as e:add('WARN','SQLite',e)
    add('OK' if os.getenv('ETHERSCAN_API_KEY','').strip() else 'WARN','Historical pool bootstrap','full history via Etherscan API' if os.getenv('ETHERSCAN_API_KEY','').strip() else 'no ETHERSCAN_API_KEY; recent RPC fallback only')
    try:
        r=requests.get(f"http://127.0.0.1:{os.getenv('DASHBOARD_PORT','8788')}/api/health",timeout=2);data=r.json() if r.ok else {};add('OK' if r.ok else 'WARN','Dashboard',f"HTTP {r.status_code}; core={data.get('hypercore_ws_age_sec')}s; wallet360={data.get('wallet360_age_sec')}s; tracked={data.get('wallet360_watch_count')}")
    except Exception:add('WARN','Dashboard','not running')
    print('HyperEVM Chain Radar Doctor V0.3.0');print('='*72)
    for s,n,d in rows:print(f'[{s}] {n}: {d}')
    print('='*72);fail=any(s=='FAIL' for s,_,_ in rows);print('STATUS:','FAIL' if fail else 'HEALTHY/WARN');raise SystemExit(1 if fail else 0)
if __name__=='__main__':main()
