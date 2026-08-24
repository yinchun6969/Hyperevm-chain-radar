#!/usr/bin/env python3
import logging,os,threading,time
from core.env import load_dotenv
load_dotenv()
from scanner import Scanner
from services.hypercore_stream import HyperCoreStream
from services.hypercore_user_stream import HyperCoreUserStream
from services.hypercore_info import HyperCoreInfoClient
from services.read_precompile import ReadPrecompile
from services.pool_bootstrap import PoolBootstrap
from intelligence.wallet360 import Wallet360Service
from services import dashboard
logging.basicConfig(level=getattr(logging,os.getenv('LOG_LEVEL','INFO').upper(),logging.INFO),format='%(asctime)s | %(levelname)s | %(threadName)s | %(message)s')
log=logging.getLogger('supervisor');stop=threading.Event()
def wrap(name,fn):
    while not stop.is_set():
        try:fn()
        except Exception:log.exception('%s crashed',name)
        stop.wait(2)
def main():
    scan=Scanner();store=scan.store;ws_url=os.getenv('HYPERCORE_WS_URL','wss://api.hyperliquid.xyz/ws')
    ws=HyperCoreStream(store,ws_url,scan.correlator,scan.tg);bootstrap=PoolBootstrap(scan.rpc,store)
    info=HyperCoreInfoClient(os.getenv('HYPERCORE_INFO_URL','https://api.hyperliquid.xyz/info'),float(os.getenv('HYPERCORE_INFO_TIMEOUT','8')))
    wallet360=Wallet360Service(store,info,ReadPrecompile(scan.rpc),scan.tg);user_ws=HyperCoreUserStream(store,scan.tg,ws_url)
    tasks={'hyperevm-scanner':lambda:scan.run(stop),'hypercore-ws':lambda:ws.run(stop),'smart-wallet-ws':lambda:user_ws.run(stop),'wallet360':lambda:wallet360.run(stop),'pool-bootstrap':lambda:bootstrap.run(stop),'dashboard':lambda:dashboard.run(store,os.getenv('DASHBOARD_HOST','127.0.0.1'),int(os.getenv('DASHBOARD_PORT','8788')))}
    for n,f in tasks.items():threading.Thread(target=wrap,args=(n,f),name=n,daemon=True).start()
    log.info('HyperEVM Chain Radar V0.3.0 started')
    try:
        while True:time.sleep(30)
    except KeyboardInterrupt:stop.set()
if __name__=='__main__':main()
