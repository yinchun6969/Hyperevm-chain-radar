from core.keccak import topic
from chains.hyperevm import HYPE_SYSTEM,is_core_system_address,topic_addr
TRANSFER=topic('Transfer(address,address,uint256)')
RECEIVED=topic('Received(address,uint256)')
def parse(log):
    addr=(log.get('address') or '').lower(); topics=log.get('topics') or []; data=log.get('data') or '0x'
    if addr==HYPE_SYSTEM and topics and topics[0].lower()==RECEIVED.lower() and len(topics)>=2:
        return {'kind':'core_transfer','direction':'EVM_TO_CORE','token':'HYPE','actor':topic_addr(topics[1]),'raw':int(data,16) if data!='0x' else 0,'decimals':18,'confidence':'exact'}
    if topics and topics[0].lower()==TRANSFER.lower() and len(topics)>=3:
        frm,to=topic_addr(topics[1]),topic_addr(topics[2]); amount=int(data,16) if data!='0x' else 0
        if is_core_system_address(to):return {'kind':'core_transfer','direction':'EVM_TO_CORE','token':addr,'actor':frm,'system':to,'raw':amount,'confidence':'exact'}
        if is_core_system_address(frm):return {'kind':'core_transfer','direction':'CORE_TO_EVM','token':addr,'actor':to,'system':frm,'raw':amount,'confidence':'exact'}
    return None
