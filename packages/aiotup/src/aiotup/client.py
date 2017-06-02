import logging
import asyncio
import random
import aiohttp
from aiochannel import Channel
from aiochannel.errors import ChannelClosed
from urllib.parse import urljoin
import json
import websockets
import uuid
import aiotup.config as config
import aiotup.discovery as dsc
from aiotup.exceptions import ConnectionError

try:
    import selectors
except ImportError:
    from asyncio import selectors

class HttpClient:
    def __init__(self, url_prefix='http://localhost:8080'):
        self.url_prefix = url_prefix
        self.session = aiohttp.ClientSession()

    async def request(self, srv, method, *params):
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '::' + method
        payload = {
            'id': uuid.uuid4().hex,
            'method': method,
            'params': params
            }
        async with self.session.post(url, json=payload, timeout=10) as resp:
            ret = await resp.text()
            return ret

class WebSocketClient:
    def __init__(self, url_prefix='ws://localhost:8080'):
        self.session = aiohttp.ClientSession()        
        self.url_prefix = url_prefix
        self.waiters = {}
        self.ws = None
        self.notify_channel = None
        self.cont = True
        asyncio.ensure_future(self.connect_wait())

    @property
    def connected(self):
        return not not self.ws

    def close(self):
        self.cont = False
        if self.ws:
            self.ws.close()
            self.ws = None

    async def connect(self):
        if self.ws:
            logging.debug('connect to %s already connected',
                          self.url_prefix)
            return
        
        url = self.url_prefix + '/jsonrpc/2.0/ws'
        try:
            ws = await self.session.ws_connect(url, autoclose=False, autoping=False, heartbeat=1.0)
            self.ws = ws
        except OSError:
            logging.warn('connect to %s failed', url)

    async def request(self, srv, method, *params):
        if not self.connected:
            raise ConnectionError('websocket closed')
        
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '::' + method
        req_id = uuid.uuid4().hex
        payload = {
            'id': req_id,
            'method': method,
            'params': params
            }

        channel = Channel(1)
        self.waiters[req_id] = channel
        try:
            await self.ws.send_json(payload)
            r = await channel.get()
            #del self.waiters[req_id]
            return r
        except ChannelClosed:
            raise ConnectionError(
                'websocket closed on sending req')
        finally:
            channel.close()

    async def onclosed(self):
        self.ws = None        
        for req_id, channel in self.waiters.items():
            channel.close()
        self.waiters = {}

    async def connect_wait(self):
        while self.cont:
            if not self.ws:
                await self.connect()
            if not self.ws:
                await asyncio.sleep(1.0)
                continue
            #try:

            #except websockets.exceptions.ConnectionClosed:
            #    return await self.onclosed()
            msg = await self.ws.receive()            
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
            elif msg.type == aiohttp.WSMsgType.BINARY:
                continue
            elif msg.type == aiohttp.WSMsgType.PING:
                self.ws.pong()
                continue
            elif msg.type == aiohttp.WSMsgType.PONG:
                continue
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                #yield from ws.close()
                return await self.onclosed()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                #print('Error during receive %s' % self.ws.exception())
                logging.debug('error during received %s', self.ws.exception())
                return await self.onclosed()
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print('closed')
                return

            #data = json.loads(data)
            req_id = data.get('id')
            if req_id:
                channel = self.waiters.get(req_id)
                if channel:
                    del self.waiters[req_id]
                    await channel.put(data)
                else:
                    logging.warn('Cannot find channel by id ', req_id)
            else:
                logging.debug('no reqid seems a notify', data)

class MethodRef:
    def __init__(self, name, srv_ref):
        self.name = name
        self.srv_ref = srv_ref
        self.kw = {}

    def options(self, **kw):
        self.kw.update(kw)
        return self

    async def __call__(self, *params):
        return await self.srv_ref.engine.request(
            self.srv_ref.name,
            self.name,
            *params,
            **self.kw)

class ServiceRef:
    def __init__(self, srv_name, engine):
        self.name = srv_name
        self.engine = engine

    def __getattr__(self, name):
        return MethodRef(name, self)

class FullConnectEngine:
    FIRST = 1
    RANDOM = 2
    def __init__(self):
        self.pool = {}
        self.policy = self.FIRST
        #self.policy = 'RANDOM'

    async def ensure_clients(self, srv):
        agent = dsc.client_agent
        assert agent

        boxes = agent.route[srv]
        for box in boxes:
            if box not in self.pool:
                # add box to pool
                client = WebSocketClient('ws://' + box)
                self.pool[box] = client

        for box, client in list(self.pool.items()):
            if box not in agent.boxes:
                logging.warning('remove box %s', box)
                # remove box due to server done
                client.close()
                del self.pool[box]

        for _ in range(30):
            c = self.get_client(srv, policy=self.FIRST)
            if c:
                return
            await asyncio.sleep(0.01)

    def get_client(self, srv, policy=None):
        policy = policy or self.policy
        agent = dsc.client_agent
        clients = []
        for box in agent.route[srv]:
            client = self.pool.get(box)
            if client.connected:
                if policy == self.FIRST:
                    return client
                else:
                    assert policy == self.RANDOM
                    clients.append(client)
        if clients:
            return random.choice(clients)
        
    def __getattr__(self, name):
        if name not in self.pool:
            raise AttributeError
        return ServiceRef(name, self)

    async def request(self, srv, method, *params, conn_retry=0, retry=0):
        agent = dsc.client_agent
        assert agent
        await self.ensure_clients(srv)
        client = self.get_client(srv)
        if not client:
            raise ConnectionError(
                'no available rpc server')

        try:
            return await client.request(srv, method, *params)
        except ConnectionError:
            assert not client.connected
            if retry <= 0:
                raise ConnectionError(
                    'cannot retry connections')
            
        return await self.request(srv, method,
                                  *params,
                                  conn_retry=conn_retry,
                                  retry=retry-1)
    
#engine = MasterStandbyEngine()
engine = FullConnectEngine()
