import tempfile,unittest
from pathlib import Path
from core.keccak import topic
from chains.hyperevm import is_core_system_address,classify_block,HYPE_SYSTEM,CORE_WRITER
from adapters import core_transfers,corewriter,hyperswap_v3
from core.storage import Store
from intelligence.lp_rug import LPRugRadar
class DummyTG:
    def __init__(self):self.sent=[]
    def send(self,x):self.sent.append(x);return True
def taddr(a):return '0x'+'0'*24+a[2:].lower()
class Tests(unittest.TestCase):
    def test_keccak_transfer(self):self.assertEqual(topic('Transfer(address,address,uint256)'),'0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef')
    def test_system_address(self):
        self.assertTrue(is_core_system_address('0x20000000000000000000000000000000000000c8'));self.assertFalse(is_core_system_address('0x21000000000000000000000000000000000000c8'))
    def test_dual_block(self):
        self.assertEqual(classify_block({'gasLimit':hex(2_000_000)}),'small');self.assertEqual(classify_block({'gasLimit':hex(30_000_000)}),'big')
    def test_hype_received(self):
        user='0x1111111111111111111111111111111111111111';log={'address':HYPE_SYSTEM,'topics':[core_transfers.RECEIVED,taddr(user)],'data':hex(10**18)};x=core_transfers.parse(log);self.assertEqual(x['direction'],'EVM_TO_CORE');self.assertEqual(x['actor'],user)
    def test_erc20_core_to_evm(self):
        token='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';sys='0x20000000000000000000000000000000000000c8';user='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';log={'address':token,'topics':[core_transfers.TRANSFER,taddr(sys),taddr(user)],'data':hex(123)};x=core_transfers.parse(log);self.assertEqual(x['direction'],'CORE_TO_EVM')
    def test_corewriter_decode(self):
        raw=bytes([1,0,0,7])+b'\x00'*64;off=(32).to_bytes(32,'big');ln=len(raw).to_bytes(32,'big');pad=raw+b'\x00'*((32-len(raw)%32)%32);tx={'to':CORE_WRITER,'input':'0x12345678'+(off+ln+pad).hex()};x=corewriter.parse_tx(tx);self.assertEqual(x['action_id'],7);self.assertEqual(x['version'],1)
    def test_pool_created(self):
        t0='0x1111111111111111111111111111111111111111';t1='0x2222222222222222222222222222222222222223';pool='0x3333333333333333333333333333333333333334';tick=(60).to_bytes(32,'big').hex();p=('0'*24+pool[2:]).rjust(64,'0');log={'address':'0xB1c0fa0B789320044A6F623cFe5eBda9562602E3','topics':[hyperswap_v3.POOL_CREATED,taddr(t0),taddr(t1),hex(3000)],'data':'0x'+tick+p};x=hyperswap_v3.parse_pool_created(log);self.assertEqual(x['pool'],pool);self.assertEqual(x['fee'],3000)
    def test_lp_rug(self):
        with tempfile.TemporaryDirectory() as td:
            s=Store(Path(td)/'x.db');tg=DummyTG();r=LPRugRadar(s,tg,abs_usd=1_000_000,p0_pct=50,p1_pct=30,baseline_min=500_000,cooldown=900);self.assertIsNone(r.on_lp('0xpool','ADD_LP',2_000_000));self.assertEqual(r.on_lp('0xpool','REMOVE_LP',1_100_000),'P0');self.assertEqual(len(tg.sent),1)
if __name__=='__main__':unittest.main()
