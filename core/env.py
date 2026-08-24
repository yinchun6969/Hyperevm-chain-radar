from __future__ import annotations
import os
from pathlib import Path

def load_dotenv(path=None):
    p=Path(path) if path else Path(__file__).resolve().parents[1]/'.env'
    if not p.exists():
        return
    for raw in p.read_text(encoding='utf-8').splitlines():
        s=raw.strip()
        if not s or s.startswith('#') or '=' not in s:
            continue
        k,v=s.split('=',1); k=k.strip(); v=v.strip()
        if len(v)>=2 and v[0]==v[-1] and v[0] in "'\"":
            v=v[1:-1]
        os.environ.setdefault(k,v)
