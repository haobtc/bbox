import os
import json
import sys

class Config:
    instance = None
    
    def __init__(self, c):
        self.c = c

    @property
    def language(self):
        return self.c['language']
    
    @property
    def name(self):
        return self.c['name']

    @property
    def etcd_list(self):
        return self.c['etcd']

    def __getitem__(self, key):
        return self.c[key]

    def get(self, key, default=None):
        return self.c.get(key, default=default)

    @classmethod
    def parse(cls):
        ''' Parse config from $PWD/tup.config.json
        '''
        if cls.instance:
            return cls.instance
        
        config_path = os.path.join(os.getcwd(),
                                   'tup.config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            cls.instance = cls(json.load(f))
        return cls.instance
