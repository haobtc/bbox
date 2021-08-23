from typing import Dict, Any, List, Union, Iterable, Set
import re, os
import time
import json
import sys
from aiobbox.utils import get_bbox_path, localbox_ip

import aiobbox.testing as testing

class Ticket:
    loaded: bool = False
    name: str
    prefix: str
    bind_ip: str = '127.0.0.1'
    language: str = 'python3'
    etcd: List[str] = []
    extbind: str = ''
    port_range = List[int]
    loadtime: int

    def load(self) -> None:
        path = get_bbox_path('ticket.json')
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                self.loaded = True
                kw = json.load(f)
                self.name = kw['name']
                prefix = kw['prefix']
                if testing.test_mode():
                    prefix = prefix + '_test'
                self.prefix = prefix
                self.bind_ip = kw.get('bind_ip', '127.0.0.1')
                self.port_range = kw['port_range']
                self.language = kw.get('language', 'python3')
                self.etcd = kw['etcd']
                self.extbind = kw.get('extbind', '')
                self.loadtime = int(time.time())

                self.validate()

    def validate(self) -> None:
        assert re.match(r'[0-9a-zA-Z\_\.\-\+]+$', self.prefix)
        # TODO: add more roles
        assert localbox_ip(self.bind_ip) or self.bind_ip == '0.0.0.0'

    # def keys(self) -> Iterable[str]:
    #     return self.data.keys()


_ticket = Ticket()
def get_ticket() -> Ticket:
    if not _ticket.loaded:
        _ticket.load()
    return _ticket
