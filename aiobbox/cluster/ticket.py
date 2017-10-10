import re, os
import time
import json
import sys
from aiobbox.utils import get_bbox_path, localbox_ip

import aiobbox.testing as testing

class Ticket:
    def __init__(self):
        self.data = {}

    def load(self):
        path = get_bbox_path('ticket.json')
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                kw = json.load(f)
                self.update(**kw)
                self.update(loadtime=int(time.time()))

    def update(self, **kw):
        if 'prefix' in kw and testing.test_mode:
            kw['prefix'] = kw['prefix'] + '_test'
        self.data.update(kw)
        self.validate()

    def validate(self):
        assert re.match(r'[0-9a-zA-Z\_\.\-\+]+$', self.prefix)
        # TODO: add more roles
        assert localbox_ip(self.bind_ip) or self.bind_ip == '0.0.0.0'

    def keys(self):
        return self.data.keys()

    def __getitem__(self, key):
        return self.data[key]

    def __getattr__(self, key):
        return self.data[key]

_ticket = Ticket()
def get_ticket():
    if not _ticket.data:
        _ticket.load()
    return _ticket
