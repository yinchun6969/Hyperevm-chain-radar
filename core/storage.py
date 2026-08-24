from __future__ import annotations
import json,sqlite3,time,threading
from pathlib import Path
SCHEMA="""
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,block_number INTEGER,tx_hash TEXT,source TEXT NOT NULL,kind TEXT NOT NULL,protocol TEXT,token TEXT,symbol TEXT,actor TEXT,pool TEXT,direction TEXT,usd REAL,details TEXT,UNIQUE(tx_hash,source,kind,token,direction));
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_token_ts ON events(token,ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_actor_ts ON events(actor,ts DESC);
CREATE TABLE IF NOT EXISTS pools(address TEXT PRIMARY KEY,protocol TEXT NOT NULL,token0 TEXT,token1 TEXT,fee INTEGER,created_block INTEGER,created_tx TEXT,discovered_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS lp_state(pool TEXT PRIMARY KEY,observed_add_usd REAL NOT NULL DEFAULT 0,observed_remove_usd REAL NOT NULL DEFAULT 0,observed_net_usd REAL NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS alerts(alert_key TEXT PRIMARY KEY,ts INTEGER NOT NULL,level TEXT NOT NULL,kind TEXT NOT NULL,details TEXT);
CREATE TABLE IF NOT EXISTS wallet_profiles(address TEXT PRIMARY KEY,first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL,core_buy_usd REAL NOT NULL DEFAULT 0,core_sell_usd REAL NOT NULL DEFAULT 0,evm_buy_usd REAL NOT NULL DEFAULT 0,evm_sell_usd REAL NOT NULL DEFAULT 0,core_to_evm_usd REAL NOT NULL DEFAULT 0,evm_to_core_usd REAL NOT NULL DEFAULT 0,lp_add_usd REAL NOT NULL DEFAULT 0,lp_remove_usd REAL NOT NULL DEFAULT 0,core_trade_count INTEGER NOT NULL DEFAULT 0,evm_trade_count INTEGER NOT NULL DEFAULT 0,sequence_count INTEGER NOT NULL DEFAULT 0,score INTEGER NOT NULL DEFAULT 0,tags TEXT NOT NULL DEFAULT '[]');
CREATE INDEX IF NOT EXISTS idx_wallet_score ON wallet_profiles(score DESC,last_seen DESC);
CREATE TABLE IF NOT EXISTS wallet360(address TEXT PRIMARY KEY,updated_at INTEGER NOT NULL,score INTEGER NOT NULL DEFAULT 0,account_value REAL NOT NULL DEFAULT 0,perp_ntl REAL NOT NULL DEFAULT 0,margin_used REAL NOT NULL DEFAULT 0,withdrawable REAL NOT NULL DEFAULT 0,unrealized_pnl REAL NOT NULL DEFAULT 0,perp_positions INTEGER NOT NULL DEFAULT 0,largest_perp_coin TEXT,largest_perp_usd REAL NOT NULL DEFAULT 0,hype_spot REAL NOT NULL DEFAULT 0,usdc_spot REAL NOT NULL DEFAULT 0,vault_equity REAL NOT NULL DEFAULT 0,precompile_ok INTEGER NOT NULL DEFAULT 0,precompile_l1_block INTEGER,snapshot TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS idx_wallet360_score ON wallet360(score DESC,updated_at DESC);
"""
WALLET_FIELDS={'core_buy_usd','core_sell_usd','evm_buy_usd','evm_sell_usd','core_to_evm_usd','evm_to_core_usd','lp_add_usd','lp_remove_usd','core_trade_count','evm_trade_count','sequence_count'}
class Store:
    def __init__(self,path):
        self.path=str(Path(path).expanduser());self.lock=threading.RLock();self.db=sqlite3.connect(self.path,timeout=20,check_same_thread=False);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA busy_timeout=15000');self.db.executescript(SCHEMA);self.db.commit()
    def kv_get(self,k,default=None):
        with self.lock:
            r=self.db.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone();return r[0] if r else default
    def kv_set(self,k,v):
        with self.lock:self.db.execute('INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)',(k,str(v)));self.db.commit()
    def add_event(self,**e):
        with self.lock:
            cur=self.db.execute("INSERT OR IGNORE INTO events(ts,block_number,tx_hash,source,kind,protocol,token,symbol,actor,pool,direction,usd,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(int(e.get('ts') or time.time()),e.get('block_number'),e.get('tx_hash'),e['source'],e['kind'],e.get('protocol'),e.get('token'),e.get('symbol'),e.get('actor'),e.get('pool'),e.get('direction'),e.get('usd'),json.dumps(e.get('details') or {},ensure_ascii=False,separators=(',',':'))));self.db.commit();return cur.rowcount>0
    def add_pool(self,address,protocol,token0,token1,fee,block,tx):
        with self.lock:self.db.execute('INSERT OR IGNORE INTO pools VALUES(?,?,?,?,?,?,?,?)',(address.lower(),protocol,token0.lower(),token1.lower(),fee,block,tx,int(time.time())));self.db.commit()
    def pools(self,protocol=None):
        with self.lock:
            if protocol:return [r[0] for r in self.db.execute('SELECT address FROM pools WHERE protocol=?',(protocol,))]
            return [r[0] for r in self.db.execute('SELECT address FROM pools')]
    def pool_count(self,protocol=None):
        with self.lock:
            if protocol:return int(self.db.execute('SELECT COUNT(*) FROM pools WHERE protocol=?',(protocol,)).fetchone()[0])
            return int(self.db.execute('SELECT COUNT(*) FROM pools').fetchone()[0])
    def recent(self,limit=100):
        cols=['id','ts','block_number','tx_hash','source','kind','protocol','token','symbol','actor','pool','direction','usd','details']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM events ORDER BY id DESC LIMIT ?',(limit,))]
    def actor_events(self,address,since_ts,limit=500):
        cols=['id','ts','block_number','tx_hash','source','kind','protocol','token','symbol','actor','pool','direction','usd','details']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM events WHERE actor=? AND ts>=? ORDER BY ts,id LIMIT ?',(address.lower(),int(since_ts),int(limit))).fetchall()]
    def claim_alert(self,key,level,kind,details=None):
        with self.lock:
            cur=self.db.execute('INSERT OR IGNORE INTO alerts(alert_key,ts,level,kind,details) VALUES(?,?,?,?,?)',(key,int(time.time()),level,kind,json.dumps(details or {},ensure_ascii=False,separators=(',',':'))));self.db.commit();return cur.rowcount>0
    def wallet_flow(self,address,ts=None,**delta):
        address=(address or '').lower()
        if len(address)!=42:return
        now=int(ts or time.time());delta={k:float(v or 0) if k.endswith('_usd') else int(v or 0) for k,v in delta.items() if k in WALLET_FIELDS and v}
        with self.lock:
            self.db.execute('INSERT OR IGNORE INTO wallet_profiles(address,first_seen,last_seen) VALUES(?,?,?)',(address,now,now));self.db.execute('UPDATE wallet_profiles SET last_seen=? WHERE address=?',(now,address))
            for k,v in delta.items():self.db.execute(f'UPDATE wallet_profiles SET {k}={k}+? WHERE address=?',(v,address))
            r=self.db.execute('SELECT core_buy_usd,core_sell_usd,evm_buy_usd,evm_sell_usd,core_to_evm_usd,evm_to_core_usd,lp_add_usd,lp_remove_usd,sequence_count FROM wallet_profiles WHERE address=?',(address,)).fetchone();cb,cs,eb,es,ce,ec,la,lr,seq=map(float,r)
            score=min(100,int((25 if ce>=500000 else 12 if ce>=100000 else 0)+(20 if cb>=500000 else 10 if cb>=100000 else 0)+(20 if eb>=500000 else 10 if eb>=100000 else 0)+(20 if la>=250000 else 10 if la>=100000 else 0)+(15 if seq>=1 else 0)))
            tags=[]
            if ce>=500000:tags.append('CORE→EVM WHALE')
            if cb>=500000:tags.append('CORE BUYER')
            if eb>=500000:tags.append('EVM BUYER')
            if la>=250000:tags.append('LP DEPLOYER')
            if seq>=1:tags.append('CORE→EVM→BUY→LP')
            self.db.execute('UPDATE wallet_profiles SET score=?,tags=? WHERE address=?',(score,json.dumps(tags,separators=(',',':')),address));self.db.commit()
    def top_wallets(self,limit=25):
        cols=['address','first_seen','last_seen','core_buy_usd','core_sell_usd','evm_buy_usd','evm_sell_usd','core_to_evm_usd','evm_to_core_usd','lp_add_usd','lp_remove_usd','core_trade_count','evm_trade_count','sequence_count','score','tags']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM wallet_profiles ORDER BY score DESC,last_seen DESC LIMIT ?',(int(limit),))]
    def wallet_candidates(self,min_score=60,limit=12):
        cols=['address','first_seen','last_seen','core_buy_usd','core_sell_usd','evm_buy_usd','evm_sell_usd','core_to_evm_usd','evm_to_core_usd','lp_add_usd','lp_remove_usd','core_trade_count','evm_trade_count','sequence_count','score','tags']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM wallet_profiles WHERE score>=? ORDER BY score DESC,last_seen DESC LIMIT ?',(int(min_score),int(limit)))]
    def save_wallet360(self,address,score,snapshot):
        s=snapshot or {};p=s.get('perp') or {};sp=s.get('spot') or {};pc=s.get('precompile') or {};largest=p.get('largest') or {}
        row=((address or '').lower(),int(time.time()),int(score or 0),float(p.get('account_value') or 0),float(p.get('ntl_pos') or 0),float(p.get('margin_used') or 0),float(p.get('withdrawable') or 0),float(p.get('unrealized_pnl') or 0),int(p.get('positions') or 0),largest.get('coin'),float(largest.get('usd') or 0),float(sp.get('hype') or 0),float(sp.get('usdc') or 0),float(s.get('vault_equity') or 0),1 if pc.get('ok') else 0,pc.get('l1_block_number'),json.dumps(s,ensure_ascii=False,separators=(',',':')))
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO wallet360(address,updated_at,score,account_value,perp_ntl,margin_used,withdrawable,unrealized_pnl,perp_positions,largest_perp_coin,largest_perp_usd,hype_spot,usdc_spot,vault_equity,precompile_ok,precompile_l1_block,snapshot) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',row);self.db.commit()
    def wallet360_rows(self,limit=25):
        cols=['address','updated_at','score','account_value','perp_ntl','margin_used','withdrawable','unrealized_pnl','perp_positions','largest_perp_coin','largest_perp_usd','hype_spot','usdc_spot','vault_equity','precompile_ok','precompile_l1_block','snapshot']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM wallet360 ORDER BY score DESC,updated_at DESC LIMIT ?',(int(limit),))]
    def wallet360_get(self,address):
        rows=self.wallet360_rows(1000)
        return next((x for x in rows if x['address']==(address or '').lower()),None)
