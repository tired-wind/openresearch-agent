import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(os.environ.get('OPENRESEARCH_DATA_DIR', 'data')).resolve()

def now(): return datetime.now(timezone.utc).isoformat()

def connect():
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    con=sqlite3.connect(ROOT/'research.sqlite',timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return con

def save(state):
    state['updated_at']=now()
    with connect() as con:
        con.execute('INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(state['id'],json.dumps(state,allow_nan=False)))

def load(run_id):
    with connect() as con:
        row=con.execute('SELECT payload FROM runs WHERE id=?',(run_id,)).fetchone()
    return json.loads(row[0]) if row else None

def artifact(run_id, name, value):
    folder=ROOT/'runs'/run_id
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=folder/name
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False) if not isinstance(value,str) else value)
    tmp.replace(path)
    return path
