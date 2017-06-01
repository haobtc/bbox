import logging
import random
import json
import time
import asyncio
import aio_etcd as etcd
from collections import defaultdict
from aiotup.exceptions import RegisterFailed

BOX_TTL = 10

class EtcdClient:
    def __init__(self, etcd_list, prefix):
        assert etcd_list
        assert prefix
        self.etcd_list = etcd_list
        self.prefix = prefix
        self.client = None

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
        self.client.close()
        self.client = None

class ServerAgent(EtcdClient):
    def __init__(self, prefix='', etcd=None, port_range=None, bind_ip='127.0.0.1', **kw):
        super(ServerAgent, self).__init__(etcd, prefix)
        self.port_range = port_range if port_range else (30000, 40000)
        self.bind_ip = bind_ip
        self.client = None
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
                return
            except etcd.EtcdAlreadyExist:
                logging.warn(
                    'register key conflict {}'.format(key))
                await asyncio.sleep(0.1)

        raise RegisterFailed(
            'no port alloced after retry {} times'.format(retry))

    async def update(self):
        while True:
            if not self.client or not self.bind:
                logging.warn('etcd client or bind are empty')
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
            for v in r.children:
                if v.key.split('/')[-1] == 'boxes':
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
        while True:
            logging.debug('watching boxes')
            try:
                r = await self.client.read(self.path('boxes'),
                                           recursive=True,
                                           wait=True)
                await self.get_boxes()
            except asyncio.TimeoutError:
                print('timeout error')
                logging.debug('timeout error on waiting boxes')

server_agent = None
def server_start(**local_config):
    global server_agent
    if server_agent:
        return server_agent

    server_agent = ServerAgent(**local_config)
    server_agent.connect()
    return server_agent

client_agent = None
async def client_connect(**local_config):
    global client_agent
    if client_agent:
        return client_agent

    client_agent = ClientAgent(**local_config)
    client_agent.connect()
    await client_agent.get_boxes()
    return client_agent
