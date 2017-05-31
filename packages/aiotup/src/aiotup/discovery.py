import random
import time
import asyncio
import aio_etcd as etcd
import aiotup.config as config

class DiscoverAgent:
    def __init__(self):
        self.client = None
        self.bind = None
        self.connect()

    def path(self, p):
        if p.startswith('/'):
            return '/{}{}'.format(config.local.prefix, p)
        else:
            return '/{}/{}'.format(config.local.prefix, p)

    def connect(self):
        host, port = random.choice(config.local.etcd).split(':')
        self.client = etcd.Client(
            host=host,
            port=int(port),
            allow_redirect=True)                      

    # Box related functions
    @property
    def self_box_path(self):
        return self.path('boxes/{}'.format(self.bind))
        
    async def get_boxes(self):
        try:
            r = await self.client.read(self.path('boxes'),
                                          recursive=True)
            #print(dir(r), r.children)
            
            return list(r.children)
        except etcd.EtcdKeyNotFound:
            return []

    async def pickup_bind(self):
        while True:
            port = random.choice(range(*config.local.port_range))
            bind = '{}:{}'.format(config.local.bind_ip,
                                  port)
            found = False
            for srv in await self.get_boxes():
                if srv.value == bind:
                    found = True
                    break
                
            if not found:
                key = self.path('boxes/{}'.format(bind))
                r = await self.client.write(key, bind,
                                            prevExist=False)
                if r:
                    self.bind = bind
                    break
                else:
                    print('hit with prev value {}'.format(bind))
                    asyncio.sleep(0.1)

    # Service related
    async def add_services(self, srv_names):
        assert self.bind
        ts = int(time.time())
        for srv_name in srv_names:
            key = self.path('services/{}/{}'.format(srv_name,
                                                    self.bind))
            await self.client.write(key, self.bind, ttl=10)

    async def get_services(self, srv_name, prefer=None):
        if prefer:
            key = self.path('services/{}/{}'.format(srv_name, prefer))
            r = await self.client.read(key)
            if r:
                return [r.value]
        
        key = self.path('services/{}'.format(srv_name))
        return [r.value
                for r in
                await self.client.read(key, recursive=True)]


agent = None
def start():
    global agent
    if agent:
        return agent
    config.parse_local()
    agent = DiscoverAgent()
    agent.connect()
    return agent

    
    
