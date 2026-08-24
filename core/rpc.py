from __future__ import annotations
import threading,time
from urllib.parse import urlsplit
import requests

class RPCPool:
    def __init__(self,urls,failback_sec=300):
        clean=[]
        for u in urls:
            u=(u or '').strip()
            if u and u not in clean: clean.append(u)
        if not clean: raise ValueError('no RPC URLs configured')
        self.urls=clean; self.failback_sec=max(0,int(failback_sec)); self.active=0
        self._lock=threading.RLock(); self._local=threading.local(); self._last_probe=0.0; self._id=0
        self.stats=[{'ok':0,'fail':0,'latency_ms':None,'last_error':''} for _ in clean]
    @staticmethod
    def label(url):
        try:
            p=urlsplit(url); host=p.hostname or 'rpc'
            if p.port: host+=f':{p.port}'
            return f'{p.scheme or "https"}://{host}'
        except Exception:return 'rpc://redacted'
    def _session(self,i):
        if not hasattr(self._local,'s'): self._local.s={}
        if i not in self._local.s:self._local.s[i]=requests.Session()
        return self._local.s[i]
    def _order(self):
        now=time.monotonic()
        with self._lock:
            a=self.active; order=[a]+[i for i in range(len(self.urls)) if i!=a]
            if a and self.failback_sec and now-self._last_probe>=self.failback_sec:
                self._last_probe=now; order=[0,a]+[i for i in range(len(self.urls)) if i not in (0,a)]
            return order
    def _post(self,i,payload,timeout):
        t=time.monotonic(); r=self._session(i).post(self.urls[i],json=payload,timeout=timeout); r.raise_for_status()
        return r.json(),(time.monotonic()-t)*1000
    def call(self,method,params=None,timeout=20):
        params=[] if params is None else params
        with self._lock:self._id+=1; rid=self._id
        payload={'jsonrpc':'2.0','id':rid,'method':method,'params':params}; errs=[]
        for i in self._order():
            try:
                data,lat=self._post(i,payload,timeout)
                if not isinstance(data,dict) or 'error' in data: raise RuntimeError(str(data.get('error') if isinstance(data,dict) else data))
                with self._lock:
                    self.active=i; s=self.stats[i]; s['ok']+=1; s['last_error']=''
                    s['latency_ms']=round(lat if s['latency_ms'] is None else s['latency_ms']*.7+lat*.3,1)
                return data.get('result')
            except Exception as e:
                s=self.stats[i]; s['fail']+=1; s['last_error']=str(e)[:160]; errs.append(f'{self.label(self.urls[i])}: {e}')
        raise RuntimeError('all RPCs failed: '+' | '.join(errs))
    def health(self):
        with self._lock:return [{'label':self.label(u),'active':i==self.active,**dict(self.stats[i])} for i,u in enumerate(self.urls)]
