import os,tempfile,time,unittest
from core.storage import Store
from intelligence.capital_flow import CapitalFlowCorrelator
class TG:
    def __init__(self):self.messages=[]
    def send(self,x):self.messages.append(x)
class V020(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(delete=False);self.tmp.close();self.s=Store(self.tmp.name);self.tg=TG();self.c=CapitalFlowCorrelator(self.s,self.tg,'en_US')
    def tearDown(self):
        try:self.s.db.close();os.unlink(self.tmp.name)
        except Exception:pass
    def emit(self,kind,direction,usd,tx,ts,actor='0x'+'11'*20):
        e={'ts':ts,'block_number':1,'tx_hash':tx,'source':'hyperevm','kind':kind,'protocol':'HyperSwap V3' if kind in ('SWAP','ADD_LP') else 'HyperCore','token':'0x'+'22'*20,'symbol':'TKN','actor':actor,'pool':'0x'+'33'*20 if kind=='ADD_LP' else None,'direction':direction,'usd':usd,'details':{}}
        self.s.add_event(**e);self.c.observe(e)
    def test_sequence_and_wallet_score(self):
        now=int(time.time());self.emit('CORE_EVM_TRANSFER','CORE_TO_EVM',600000,'0xa',now);self.emit('SWAP','BUY',300000,'0xb',now+60);self.emit('ADD_LP',None,300000,'0xc',now+120)
        self.assertEqual(len([e for e in self.s.recent(20) if e['kind']=='CAPITAL_SEQUENCE']),1);self.assertTrue(self.tg.messages);w=self.s.top_wallets(1)[0];self.assertGreaterEqual(w['score'],55);self.assertEqual(w['sequence_count'],1)
    def test_wrong_order_no_sequence(self):
        now=int(time.time());self.emit('SWAP','BUY',300000,'0xb',now);self.emit('CORE_EVM_TRANSFER','CORE_TO_EVM',600000,'0xa',now+60);self.emit('ADD_LP',None,300000,'0xc',now+120)
        self.assertFalse(any(e['kind']=='CAPITAL_SEQUENCE' for e in self.s.recent(20)))
if __name__=='__main__':unittest.main()
