from __future__ import annotations
import logging,os,time,requests
from chains.hyperevm import CHAIN_ID,HYPERSWAP_V3_FACTORY
from adapters.hyperswap_v3 import POOL_CREATED,parse_pool_created
log=logging.getLogger('pool-bootstrap')
class PoolBootstrap:
    FACTORY_DEPLOY_BLOCK=11648
    def __init__(self,rpc,store):
        self.rpc=rpc;self.store=store;self.key=os.getenv('ETHERSCAN_API_KEY','').strip();self.offset=min(1000,max(10,int(os.getenv('ETHERSCAN_LOG_OFFSET','1000'))));self.recent=max(0,int(os.getenv('HYPERSWAP_RPC_BOOTSTRAP_BLOCKS','5000')));self.sleep=float(os.getenv('HYPERSWAP_RPC_BOOTSTRAP_SLEEP_SEC','0.7'));self.refresh=max(900,int(os.getenv('POOL_BOOTSTRAP_REFRESH_SEC','21600')))
    def _ingest(self,logs):
        n=0
        for l in logs or []:
            x=parse_pool_created(l)
            if not x:continue
            bn=l.get('blockNumber',0);bn=int(bn,16) if isinstance(bn,str) and bn.startswith('0x') else int(bn or 0)
            self.store.add_pool(x['pool'],'HyperSwap V3',x['token0'],x['token1'],x['fee'],bn,l.get('transactionHash'));n+=1
        return n
    def _etherscan(self,latest):
        page=1;total=0
        while True:
            params={'chainid':str(CHAIN_ID),'module':'logs','action':'getLogs','fromBlock':str(self.FACTORY_DEPLOY_BLOCK),'toBlock':str(latest),'address':HYPERSWAP_V3_FACTORY,'topic0':POOL_CREATED,'page':str(page),'offset':str(self.offset),'apikey':self.key}
            r=requests.get('https://api.etherscan.io/v2/api',params=params,timeout=25);r.raise_for_status();data=r.json();rows=data.get('result')
            if not isinstance(rows,list):
                if str(data.get('message','')).lower().startswith('no'):break
                raise RuntimeError(f"Etherscan bootstrap failed: {data.get('message')} {rows}")
            total+=self._ingest(rows)
            if len(rows)<self.offset:break
            page+=1;time.sleep(.25)
        self.store.kv_set('pool_bootstrap_mode','etherscan-full');return total
    def _rpc_recent(self,latest,stop):
        start=max(self.FACTORY_DEPLOY_BLOCK,latest-self.recent);total=0
        for a in range(start,latest+1,50):
            if stop.is_set():break
            b=min(latest,a+49);logs=self.rpc.call('eth_getLogs',[{'fromBlock':hex(a),'toBlock':hex(b),'address':HYPERSWAP_V3_FACTORY,'topics':[POOL_CREATED]}],30) or [];total+=self._ingest(logs);self.store.kv_set('pool_bootstrap_cursor',b)
            if b<latest:stop.wait(self.sleep)
        self.store.kv_set('pool_bootstrap_mode',f'rpc-recent-{self.recent}');return total
    def once(self,stop):
        latest=int(self.rpc.call('eth_blockNumber'),16);before=self.store.pool_count('HyperSwap V3')
        try:
            added=self._etherscan(latest) if self.key else self._rpc_recent(latest,stop);self.store.kv_set('pool_bootstrap_last_ts',int(time.time()));self.store.kv_set('pool_bootstrap_last_added',added);self.store.kv_set('pool_bootstrap_pool_count',self.store.pool_count('HyperSwap V3'));log.info('pool bootstrap complete before=%s after=%s mode=%s',before,self.store.pool_count('HyperSwap V3'),self.store.kv_get('pool_bootstrap_mode'))
        except Exception:log.exception('pool bootstrap failed')
    def run(self,stop):
        while not stop.is_set():self.once(stop);stop.wait(self.refresh)
