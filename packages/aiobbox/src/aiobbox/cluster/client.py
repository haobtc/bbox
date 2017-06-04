import logging
import re
import random
import json
import time
import asyncio
import aio_etcd as etcd
import aiohttp
from collections import defaultdict
from aiobbox.utils import json_to_str
from aiobbox.exceptions import RegisterFailed, ETCDError
import aiobbox.config as bbox_config
from .etcd_client import EtcdClient

class ClientAgent(EtcdClient):
    agent = None

    @classmethod
    async def connect_cluster(cls, **local_config):
        if cls.agent:
            return cls.agent

        cls.agent = ClientAgent(**local_config)
        cls.agent.connect()

        await cls.agent.get_boxes()
        await cls.agent.get_configs()
    
        asyncio.ensure_future(cls.agent.watch_boxes())
        asyncio.ensure_future(cls.agent.watch_configs())    
        return cls.agent
    
    def __init__(self, etcd=None, prefix=None, **kw):
        super(ClientAgent, self).__init__(etcd, prefix)
        self.route = defaultdict(list)
        self.boxes = {}

    async def get_boxes(self):
        new_route = defaultdict(list)
        boxes = {}
        try:
            r = await self.read(self.path('boxes'),
                                recursive=True)
            for v in self.walk(r):
                m = re.match(r'/[^/]+/boxes/(?P<box>[^/]+)$', v.key)
                if not m:
                    continue
                box_info = json.loads(v.value)
                bind = box_info['bind']
                boxes[bind] = box_info
                for srv in box_info['services']:
                    new_route[srv].append(bind)
        except etcd.EtcdKeyNotFound:
            pass
        self.route = new_route
        self.boxes = boxes
        
    def get_box(self, srv):
        boxes = self.route[srv]
        return random.choice(boxes)

    async def watch_boxes(self):
        async def onchange(r):
            return await self.get_boxes()
        return await self.watch_changes('boxes', onchange)
    
    # config related
    async def set_config(self, sec, key, value):
        assert sec and key
        assert '/' not in sec
        assert '/' not in key

        etcd_key = self.path('configs/{}/{}'.format(sec, key))
        old_value = bbox_config.cluster.get(sec, key)
        value_json = json_to_str(value)
        if old_value:
            old_value_json = json_to_str(old_value)
            await self.write(etcd_key, value_json,
                             prevValue=old_value_json)
        else:
            await self.write(etcd_key, value_json,
                             prevExist=False)
        bbox_config.cluster.set(sec, key, value)        

    async def del_config(self, sec, key):
        assert sec and key
        assert '/' not in sec
        assert '/' not in key
        
        bbox_config.cluster.delete(sec, key)
        etcd_key = self.path('configs/{}/{}'.format(sec, key))
        await self.delete(etcd_key)

    async def del_section(self, sec):
        assert sec
        assert '/' not in sec
        
        bbox_config.cluster.delete_section(sec)
        etcd_key = self.path('configs/{}'.format(sec))
        await self.delete(etcd_key, recursive=True)
        
    async def clear_config(self):
        bbox_config.cluster.clear()
        etcd_key = self.path('configs')
        try:
            await self.delete(etcd_key, recursive=True)
        except etcd.EtcdKeyNotFound:
            logging.debug(
                'key %s not found on delete', etcd_key)
        
    async def get_configs(self):
        reg = r'/(?P<prefix>[^/]+)/configs/(?P<sec>[^/]+)/(?P<key>[^/]+)'        
        try:
            r = await self.read(self.path('configs'),
                                recursive=True)
            new_conf = bbox_config.ClusterConfig()
            for v in self.walk(r):
                m = re.match(reg, v.key)
                if m:
                    assert m.group('prefix') == self.prefix
                    sec = m.group('sec')
                    key = m.group('key')
                    new_conf.set(sec, key, json.loads(v.value))
                    
            bbox_config.cluster = new_conf
        except etcd.EtcdKeyNotFound:
            pass
        except ETCDError:
            pass
        
    async def watch_configs(self):
        async def onchange(r):
            return await self.get_configs()
        return await self.watch_changes('configs', onchange)
