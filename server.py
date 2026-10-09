"""Development API + static server. Python standard library only."""
import json, math, os, sqlite3, time
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('FOODBRIDGE_DB', ROOT / 'database' / 'foodbridge.sqlite3'))
CATEGORIES = {'Vegetarian', 'Non-vegetarian', 'Produce', 'Bakery'}

def connect():
    c = sqlite3.connect(DB, timeout=10)
    c.execute('PRAGMA foreign_keys=ON')
    return c

def write_state(c, s):
    c.execute('DELETE FROM deliveries'); c.execute('DELETE FROM food'); c.execute('DELETE FROM recipients')
    c.executemany('INSERT INTO food VALUES (?,?,?,?,?,?,?,?,?)', [(f['id'],f['name'],f['org'],f['qty'],f['type'],f['expiry'],f['x'],f['y'],int(f['cold'])) for f in s['food']])
    c.executemany('INSERT INTO recipients VALUES (?,?,?,?,?,?,?,?)', [(r['id'],r['name'],r['qty'],r['type'],r['priority'],r['x'],r['y'],int(r['cold'])) for r in s['requests']])
    c.executemany('INSERT INTO deliveries VALUES (?,?,?,?,?,?)', [(j['id'],j['fid'],j['rid'],j['qty'],j['status'],json.dumps(j)) for j in s['jobs']])
    c.execute('INSERT OR REPLACE INTO settings VALUES (1,?)', (json.dumps(s['settings']),))

def read_state(c):
    food=[dict(zip(['id','name','org','qty','type','expiry','x','y','cold'],row)) for row in c.execute('SELECT * FROM food ORDER BY rowid')]
    req=[dict(zip(['id','name','qty','type','priority','x','y','cold'],row)) for row in c.execute('SELECT * FROM recipients ORDER BY rowid')]
    for o in food+req: o['cold']=bool(o['cold'])
    return {'food':food,'requests':req,'jobs':[json.loads(row[0]) for row in c.execute('SELECT payload FROM deliveries ORDER BY rowid')],'settings':json.loads(c.execute('SELECT payload FROM settings WHERE id=1').fetchone()[0])}

def number(v, low, high):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and low<=v<=high

def validate(s, old):
    if not isinstance(s,dict) or set(s)!={'food','requests','jobs','settings'}: raise ValueError('Invalid workspace structure')
    for key in ('food','requests','jobs'):
        if not isinstance(s[key],list) or len(s[key])>1000: raise ValueError('Invalid record count')
        ids=[o.get('id') for o in s[key] if isinstance(o,dict)]
        if len(ids)!=len(s[key]) or any(not isinstance(i,str) or not 1<=len(i)<=100 for i in ids) or len(ids)!=len(set(ids)): raise ValueError('Invalid or duplicate record IDs')
    for o in s['food']+s['requests']:
        if not isinstance(o.get('name'),str) or not 1<=len(o['name'].strip())<=100: raise ValueError('Name required (maximum 100 characters)')
        if not number(o.get('qty'),1,100000) or int(o['qty'])!=o['qty']: raise ValueError('Quantity must be a positive integer')
        if not all(number(o.get(k),-1000,1000) for k in ('x','y')) or not isinstance(o.get('cold'),bool): raise ValueError('Invalid location or storage')
    for f in s['food']:
        if f.get('type') not in CATEGORIES or not isinstance(f.get('org'),str) or not 1<=len(f['org'].strip())<=100 or not number(f.get('expiry'),0,1e15): raise ValueError('Invalid food details')
    for r in s['requests']:
        if r.get('type') not in CATEGORIES|{'Any'} or r.get('priority') not in (1,2,3): raise ValueError('Invalid recipient details')
    cfg=s['settings']
    if not isinstance(cfg,dict) or not all(number(cfg.get(k),lo,hi) for k,lo,hi in [('radius',1,100),('capacity',1,10000),('trips',1,100),('speed',1,100),('priority',0,100)]) or not isinstance(cfg.get('cold'),bool): raise ValueError('Invalid transport settings')
    if any(int(cfg[k])!=cfg[k] for k in ('capacity','trips')): raise ValueError('Capacity and trips must be integers')
    fs={f['id']:f for f in s['food']};rs={r['id']:r for r in s['requests']};oldjobs={j['id']:j for j in old['jobs']};sf={};sr={};now=time.time()*1000
    for j in s['jobs']:
        if j.get('fid') not in fs or j.get('rid') not in rs or not number(j.get('qty'),1,100000) or int(j['qty'])!=j['qty']: raise ValueError('Invalid allocation')
        status=j.get('status'); prior=oldjobs.get(j['id'])
        if status not in {'Reserved','Picked up','Delivered','Cancelled'}: raise ValueError('Invalid delivery status')
        if prior:
            if any(j.get(k)!=prior.get(k) for k in ('fid','rid','qty','created','expiry')): raise ValueError('An allocation cannot be rewritten')
            allowed={'Reserved':{'Reserved','Picked up','Cancelled'},'Picked up':{'Picked up','Delivered','Cancelled'},'Delivered':{'Delivered'},'Cancelled':{'Cancelled'}}
            if status not in allowed[prior['status']]: raise ValueError('Invalid status transition')
        else:
            f,r=fs[j['fid']],rs[j['rid']];distance=math.hypot(f['x']-r['x'],f['y']-r['y']);eta=15+distance/cfg['speed']*60
            if not number(j.get('created'),0,1e15): raise ValueError('Invalid timestamp')
            if status!='Reserved' or j['qty']>cfg['capacity'] or distance>cfg['radius'] or f['expiry']<=now+eta*60000 or (r['type']!='Any' and r['type']!=f['type']) or (f['cold'] and not (r['cold'] and cfg['cold'])): raise ValueError('Allocation violates expiry, category, distance, or transport constraints')
            if j.get('expiry')!=f['expiry']: raise ValueError('Expiry mismatch')
            j['distance']=distance;j['eta']=eta;j['food']=f['name'];j['recipient']=r['name']
        if prior and prior['status']=='Reserved' and status=='Picked up' and j['expiry']<=now: raise ValueError('Cannot pick up expired food')
        if prior and prior['status']!='Delivered' and status=='Delivered': j['deliveredAt']=now;j['late']=j['expiry']<=now
        if status!='Cancelled': sf[j['fid']]=sf.get(j['fid'],0)+j['qty'];sr[j['rid']]=sr.get(j['rid'],0)+j['qty']
    if any(q>fs[i]['qty'] for i,q in sf.items()) or any(q>rs[i]['qty'] for i,q in sr.items()): raise ValueError('Allocated quantity exceeds supply or demand')
    new_active=sum(j['status'] in ('Reserved','Picked up') for j in s['jobs'])
    if any(j['id'] not in oldjobs for j in s['jobs']) and new_active>cfg['trips']: raise ValueError('Concurrent trip budget exceeded')
    if not set(oldjobs).issubset({j['id'] for j in s['jobs']}): raise ValueError('Use reset endpoint to clear history')

def initialize():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with connect() as c:
        c.executescript((ROOT/'database/schema.sql').read_text())
        if not c.execute('SELECT 1 FROM workspace').fetchone():
            s=json.loads((ROOT/'database/seed.json').read_text());now=time.time()*1000
            for f in s['food']: f['expiry']=now+f.pop('expiresInHours')*3600000
            c.execute('INSERT INTO workspace VALUES (1,0)');write_state(c,s)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'frontend'),**kwargs)
    def reply(self,status,body):
        data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/api/state':
            with connect() as c: self.reply(200,{'revision':c.execute('SELECT revision FROM workspace WHERE id=1').fetchone()[0],'state':read_state(c)})
        elif self.path=='/api/health': self.reply(200,{'status':'ok'})
        elif self.path.startswith('/api/'): self.reply(404,{'error':'Unknown endpoint'})
        else: super().do_GET()
    def do_PUT(self):
        if self.path!='/api/state': return self.reply(404,{'error':'Unknown endpoint'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2_000_000: return self.reply(413,{'error':'Request too large or empty'})
            data=json.loads(self.rfile.read(size))
            with connect() as c:
                c.execute('BEGIN IMMEDIATE');rev=c.execute('SELECT revision FROM workspace WHERE id=1').fetchone()[0]
                if data.get('revision')!=rev: return self.reply(409,{'error':'Another session updated these records'})
                s=data['state'];validate(s,read_state(c));write_state(c,s);c.execute('UPDATE workspace SET revision=revision+1 WHERE id=1')
            self.reply(200,{'revision':rev+1})
        except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e: self.reply(400,{'error':str(e)})
    def do_POST(self):
        if self.path!='/api/reset': return self.reply(404,{'error':'Unknown endpoint'})
        with connect() as c:
            c.execute('BEGIN IMMEDIATE');s=json.loads((ROOT/'database/seed.json').read_text())
            for f in s['food']: f['expiry']=time.time()*1000+f.pop('expiresInHours')*3600000
            write_state(c,s);c.execute('UPDATE workspace SET revision=revision+1 WHERE id=1')
        self.reply(200,{'status':'reset'})

if __name__=='__main__':
    initialize();port=int(os.environ.get('PORT','8000'));print(f'FoodBridge: http://localhost:{port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
