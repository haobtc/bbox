import re, os
import time
import json
import logging
import sys
from aiobbox.utils import abs_path, home_path, localbox_ip

class Ticket:
    def __init__(self):
        self.data = {}
        
    def load(self, config_path=None):
        config_path_list = []
        if config_path is not None:
            config_path_list.append(config_path)
        
        config_path_list.append(abs_path(
            'bbox.ticket.json'))
        config_path_list.append(home_path(
            '.bbox/ticket.json'))
        
        for path in config_path_list:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    kw = json.load(f)
                    self.update(**kw)
                    self.update(loadtime=int(time.time()))
                    break

    def update(self, **kw):
        self.data.update(kw)
        self.validate()
        
    def validate(self):
        assert re.match(r'[0-9a-zA-Z\_\.\-\+]+$', self.prefix)
        # TODO: add more roles
        assert localbox_ip(self.bind_ip)

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
