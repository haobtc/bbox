import os
import json
import sys

class LocalConfig:
    '''
    Local config read from $PWD/tup.config.json
    '''
    def __init__(self, c):
        self.c = c

    def __getattr__(self, key):
        return self.c[key]

    def __getitem__(self, key):
        return self.c[key]

    def get(self, key, default=None):
        return self.c.get(key, default=default)

    @classmethod
    def parse(cls):
        ''' Parse config from $PWD/tup.config.json
        '''
        config_path = os.path.join(os.getcwd(),
                                   'tup.config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            return cls(json.load(f))
    
local = None
def parse_local():
    global local
    if local is None:
        local = LocalConfig.parse()
        # validaty
        assert local.port_range[0] < local.port_range[1]
    return local
