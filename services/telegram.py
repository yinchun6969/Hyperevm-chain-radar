from __future__ import annotations
import requests
class Telegram:
    def __init__(self,token='',chat_id=''):self.token=token.strip();self.chat_id=chat_id.strip()
    @property
    def enabled(self):return bool(self.token and self.chat_id)
    def send(self,text):
        if not self.enabled:return False
        r=requests.post(f'https://api.telegram.org/bot{self.token}/sendMessage',json={'chat_id':self.chat_id,'text':text,'disable_web_page_preview':True},timeout=10);r.raise_for_status();return True
