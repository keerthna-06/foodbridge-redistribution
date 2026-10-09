import importlib.util, json, tempfile, unittest, time
from pathlib import Path
spec=importlib.util.spec_from_file_location('server',Path(__file__).resolve().parents[1]/'backend/server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();s.DB=Path(self.tmp.name)/'test.sqlite3';s.initialize()
        with s.connect() as c:self.old=s.read_state(c)
        self.state=json.loads(json.dumps(self.old))
    def tearDown(self):self.tmp.cleanup()
    def job(self,qty=30):
        f=self.state['food'][0];r=self.state['requests'][0]
        self.state['jobs'].append(dict(id='j1',fid=f['id'],rid=r['id'],qty=qty,status='Reserved',expiry=f['expiry'],created=time.time()*1000))
    def test_persistence(self):
        self.state['food'][0]['name']='Updated food'
        s.validate(self.state,self.old)
        with s.connect() as c:s.write_state(c,self.state)
        with s.connect() as c:self.assertEqual(s.read_state(c)['food'][0]['name'],'Updated food')
    def test_partial_allocation(self):self.job();s.validate(self.state,self.old)
    def test_overallocation(self):
        self.job(81)
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_expiry(self):
        self.state['food'][0]['expiry']=time.time()*1000-1;self.job()
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_category(self):
        self.state['requests'][0]['type']='Bakery';self.job()
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_distance(self):
        self.state['settings']['radius']=1;self.state['requests'][0]['x']=100;self.job()
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_cold_chain(self):
        self.state['food'][0]['cold']=True;self.state['settings']['cold']=False;self.job()
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_trip_budget(self):
        self.state['settings']['trips']=1;self.job(20);second=dict(self.state['jobs'][0],id='j2');self.state['jobs'].append(second)
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
    def test_history_transition(self):
        self.job();s.validate(self.state,self.old);old=json.loads(json.dumps(self.state));old['jobs'][0]['status']='Delivered'
        with self.assertRaises(ValueError):s.validate(self.state,old)
    def test_integer_quantities(self):
        self.state['food'][0]['qty']=10.5
        with self.assertRaises(ValueError):s.validate(self.state,self.old)
if __name__=='__main__':unittest.main()
