from __future__ import annotations
import json,sqlite3,time,threading
from pathlib import Path
SCHEMA="""
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,block_number INTEGER,tx_hash TEXT,source TEXT NOT NULL,kind TEXT NOT NULL,protocol TEXT,token TEXT,symbol TEXT,actor TEXT,pool TEXT,direction TEXT,usd REAL,details TEXT,UNIQUE(tx_hash,source,kind,token,direction));
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_token_ts ON events(token,ts DESC);
CREATE TABLE IF NOT EXISTS pools(address TEXT PRIMARY KEY,protocol TEXT NOT NULL,token0 TEXT,token1 TEXT,fee INTEGER,created_block INTEGER,created_tx TEXT,discovered_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS lp_state(pool TEXT PRIMARY KEY,observed_add_usd REAL NOT NULL DEFAULT 0,observed_remove_usd REAL NOT NULL DEFAULT 0,observed_net_usd REAL NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS alerts(alert_key TEXT PRIMARY KEY,ts INTEGER NOT NULL,level TEXT NOT NULL,kind TEXT NOT NULL,details TEXT);
"""
class Store:
    def __init__(self,path):
        self.path=str(Path(path).expanduser()); self.lock=threading.RLock(); self.db=sqlite3.connect(self.path,timeout=20,check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA busy_timeout=15000'); self.db.executescript(SCHEMA); self.db.commit()
    def kv_get(self,k,default=None):
        with self.lock:
            r=self.db.execute('SELECT v FROM kv WHERE k=?',(k,)).fetchone(); return r[0] if r else default
    def kv_set(self,k,v):
        with self.lock:self.db.execute('INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)',(k,str(v))); self.db.commit()
    def add_event(self,**e):
        with self.lock:
            cur=self.db.execute("INSERT OR IGNORE INTO events(ts,block_number,tx_hash,source,kind,protocol,token,symbol,actor,pool,direction,usd,details) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(int(e.get('ts') or time.time()),e.get('block_number'),e.get('tx_hash'),e['source'],e['kind'],e.get('protocol'),e.get('token'),e.get('symbol'),e.get('actor'),e.get('pool'),e.get('direction'),e.get('usd'),json.dumps(e.get('details') or {},ensure_ascii=False,separators=(',',':')))); self.db.commit(); return cur.rowcount>0
    def add_pool(self,address,protocol,token0,token1,fee,block,tx):
        with self.lock:self.db.execute('INSERT OR IGNORE INTO pools VALUES(?,?,?,?,?,?,?,?)',(address.lower(),protocol,token0.lower(),token1.lower(),fee,block,tx,int(time.time()))); self.db.commit()
    def pools(self,protocol=None):
        with self.lock:
            if protocol:return [r[0] for r in self.db.execute('SELECT address FROM pools WHERE protocol=?',(protocol,))]
            return [r[0] for r in self.db.execute('SELECT address FROM pools')]
    def recent(self,limit=100):
        cols=['id','ts','block_number','tx_hash','source','kind','protocol','token','symbol','actor','pool','direction','usd','details']
        with self.lock:return [dict(zip(cols,r)) for r in self.db.execute('SELECT * FROM events ORDER BY id DESC LIMIT ?',(limit,))]
