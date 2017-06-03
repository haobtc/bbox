import logging
import re
import random
import json
import time
import asyncio
import aio_etcd as etcd
from collections import defaultdict
from aiobbox.exceptions import RegisterFailed
import aiobbox.config as bbox_config

BOX_TTL = 10

class EtcdClient:
    def __init__(self, etcd_list, prefix):
        assert etcd_list
        assert prefix
        self.etcd_list = etcd_list
        self.prefix = prefix
        self.client = None
        self.cont = True

    def path(self, p):
        if p.startswith('/'):
            return '/{}{}'.format(self.prefix, p)
        else:
            return '/{}/{}'.format(self.prefix, p)

    def connect(self):
        host, port = random.choice(self.etcd_list).split(':')
        self.client = etcd.Client(
            host=host,
            port=int(port),
            allow_redirect=True)

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
        self.cont = False

    def walk(self, v):
        yield v
        for c in v.children:
            if c.key == v.key:
                continue
            for cc in self.walk(c):
                yield cc

    async def watch_changes(self, component, changed):
        while self.cont:
            logging.debug('watching %s', component)
            try:
                chg = await self.client.read(self.path(component),
                                           recursive=True,
                                           wait=True)
                await changed(chg)
            except asyncio.TimeoutError:
                logging.debug('timeout error during watching %s', component)
            except KeyError:
                logging.debug('key error during watching %s', component)

class ServerAgent(EtcdClient):
    def __init__(self, prefix='', etcd=None, port_range=None, bind_ip='127.0.0.1', **kw):
        super(ServerAgent, self).__init__(etcd, prefix)
        self.port_range = port_range if port_range else (30000, 40000)
        self.bind_ip = bind_ip
        self.bind = None
        self.srv_names = []

    async def register(self, srv_names, retry=100):
        for _ in range(retry + 1):
            if self.bind:
                return
            port = random.choice(range(*self.port_range))
            bind = '{}:{}'.format(self.bind_ip,
                                  port)

            key = self.path('boxes/{}'.format(bind))
            value = json.dumps({
                'bind': bind,
                'services': srv_names,
                })
            try:
                await self.client.write(key, value,
                                        ttl=BOX_TTL,
                                        prevExist=False)
                self.bind = bind
                self.srv_names = srv_names
                asyncio.ensure_future(server_agent.update())
                return
            except etcd.EtcdAlreadyExist:
                logging.warn(
                    'register key conflict {}'.format(key))
                await asyncio.sleep(0.1)

        raise RegisterFailed(
            'no port alloced after retry {} times'.format(retry))

    async def deregister(self):
        if not self.bind or not self.client:
            return
        key = self.path('boxes/{}'.format(self.bind))
        await self.client.delete(key)

    async def update(self):
        while True:
            if not self.client or not self.bind:
                logging.debug('etcd client or bind are empty')
            else:
                key = self.path('boxes/{}'.format(self.bind))
                await self.client.refresh(key, ttl=BOX_TTL)
            await asyncio.sleep(3)

class ClientAgent(EtcdClient):
    def __init__(self, etcd=None, prefix=None, **kw):
        super(ClientAgent, self).__init__(etcd, prefix)
        self.route = defaultdict(list)
        self.boxes = defaultdict(list)

    async def get_boxes(self):
        new_route = defaultdict(list)
        boxes = defaultdict(list)
        try:
            r = await self.client.read(self.path('boxes'),
                                       recursive=True)
            for v in self.walk(r):
                m = re.match(r'/[^/]+/boxes/(?P<box>[^/]+)$', v.key)
                if not m:
                    continue
                info = json.loads(v.value)
                boxes[info['bind']] = info['services']
                for srv in info['services']:
                    new_route[srv].append(info['bind'])
        except etcd.EtcdKeyNotFound:
            pass
        self.route = new_route
        self.boxes = boxes
        
    def get_box(self, srv):
        boxes = self.route[srv]
        return random.choice(boxes)

    async def watch_boxes(self):
        async def onchange(r):
            return self.get_boxes()
        return await self.watch_changes('boxes', onchange)
    
    # config related
    async def set_config(self, sec, key, value):
        assert sec
        assert key
        assert '/' not in sec
        assert '/' not in key

        etcd_key = self.path('configs/{}/{}'.format(sec, key))
        old_value = bbox_config.grand.get(sec, key)
        value_json = json.dumps(value, sort_keys=True)
        if old_value:
            old_value_json = json.dumps(old_value, sort_keys=True)
            await self.client.write(etcd_key, value_json, prevValue=old_value_json)
        else:
            await self.client.write(etcd_key, value_json, prevExist=False)

        bbox_config.grand.set(sec, key, value)        

    async def del_config(self, sec, key):
        assert sec
        assert key
        assert '/' not in sec
        assert '/' not in key
        
        bbox_config.grand.delete(sec, key)
        etcd_key = self.path('configs/{}/{}'.format(sec, key))
        await self.client.delete(etcd_key)

    async def del_section(self, sec):
        assert sec
        assert '/' not in sec
        
        bbox_config.grand.delete_section(sec)
        etcd_key = self.path('configs/{}'.format(sec))
        await self.client.delete(etcd_key, recursive=True)
        
    async def clear_config(self):
        bbox_config.grand.clear()
        etcd_key = self.path('configs')
        try:
            await self.client.delete(etcd_key, recursive=True)
        except etcd.EtcdKeyNotFound:
            logging.debug('key %s not found on delete', etcd_key)
        
    async def get_configs(self):
        reg = r'/(?P<prefix>[^/]+)/configs/(?P<sec>[^/]+)/(?P<key>[^/]+)'        
        try:
            r = await self.client.read(self.path('configs'),
                                       recursive=True)
            new_conf = bbox_config.GrandConfig()
            for v in self.walk(r):
                m = re.match(reg, v.key)
                if m:
                    assert m.group('prefix') == self.prefix
                    sec = m.group('sec')
                    key = m.group('key')
                    new_conf.set(sec, key, json.loads(v.value))
                    
            bbox_config.grand = new_conf
        except etcd.EtcdKeyNotFound:
            pass

    async def watch_configs(self):
        async def onchange(r):
            return await self.get_configs()
        return await self.watch_changes('configs', onchange)

server_agent = None
async def server_start(**local_config):
    global server_agent
    if server_agent:
        return server_agent

    server_agent = ServerAgent(**local_config)
    server_agent.connect()
    #asyncio.ensure_future(server_agent.update())    
    return server_agent

client_agent = None
async def client_connect(**local_config):
    global client_agent
    if client_agent:
        return client_agent

    client_agent = ClientAgent(**local_config)
    client_agent.connect()
    
    await asyncio.gather(
        client_agent.get_boxes(),
        client_agent.get_configs())
    
    asyncio.ensure_future(client_agent.watch_boxes())
    asyncio.ensure_future(client_agent.watch_configs())    
    return client_agent
