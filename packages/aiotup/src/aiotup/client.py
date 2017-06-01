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

class HttpClient:
    def __init__(self, url_prefix='http://localhost:8080'):
        self.url_prefix = url_prefix

    async def request(self, srv, method, *params):
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '::' + method
        payload = {
            'id': uuid.uuid4().hex,
            'method': method,
            'params': params
            }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    url,
                    json=payload
            ) as resp:
                ret = await resp.text()
                return ret

class WebSocketClient:
    def __init__(self, url_prefix='ws://localhost:8080'):
        self.url_prefix = url_prefix
        self.waiters = {}
        self.ws = None

    def close(self):
        print('close')
        if self.ws:
            self.ws.close()
            self.ws = None

    async def connect(self):
        if self.ws:
            print('already connected')
            return
        url = self.url_prefix + '/jsonrpc/2.0/ws'
        self.ws = await websockets.connect(url)
        asyncio.ensure_future(self.wait())

    async def request(self, srv, method, *params):
        if not self.ws:
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
            await self.ws.send(json.dumps(payload))
            return await channel.get()
        finally:
            channel.close()

    async def onclosed(self):
        for req_id, channel in self.waiters.items():
            channel.close()
            # data = {'id': req_id,
            #         'error': {
            #             'code': 'close',
            #             'message': 'connection closed by peer'},
            #         'result': None}
            # await channel.put(data)
        self.waiters = {}
        self.ws = None

    async def wait(self):
        while True:
            try:
                data = await self.ws.recv()
            except websockets.exceptions.ConnectionClosed:
                return await self.onclosed()

            data = json.loads(data)
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

class MasterStandbyEngine:
    def __init__(self):
        self.pool = {}

    async def connect(self):
        assert config.local
        await dsc.client_connect(**config.local)

    def close(self):
        if dsc.client_agent:
            dsc.client_agent.close()
            dsc.client_agent = None
        self.pool = {}

    def __getattr__(self, name):
        if name not in self.pool:
            raise AttributeError
        return ServiceRef(name, self)

    async def request(self, srv, method, *params, conn_retry=0, retry=0):
        agent = dsc.client_agent
        assert agent
        if srv in self.pool:
            client = self.pool[srv]
        else:
            boxes = agent.route.get(srv)
            if not boxes:
                raise ConnectionError(
                    'no available rpc server')

            bad_boxes = []
            boxes = random.sample(boxes, len(boxes))

            # retry connect some times
            for _ in range(conn_retry + 1):
                if boxes:
                    box = boxes.pop()
                else:
                    box = random.choice(bad_boxes)

                logging.debug('got box %s for service %s', box, srv)
                client = WebSocketClient('ws://' + box)
                try:
                    await client.connect()
                    self.pool[srv] = client
                    break
                except OSError:
                    logging.error('cannot connect to %s', box)
                    bad_boxes.append(box)

            if srv not in self.pool:
                raise ConnectionError(
                    'all connection for service {} failed'.format(srv))
        try:
            return await client.request(srv, method, *params)
        except (ChannelClosed, ConnectionError):
            logging.error('channel closed')
            client.close()
            if srv in self.pool:
                del self.pool[srv]
            if retry <= 0:
                raise ConnectionError(
                    'cannot retry connections')
            
        return await self.request(srv, method,
                                  *params,
                                  conn_retry=conn_retry,
                                  retry=retry-1)

class FullConnectEngine:
    def __init__(self):
        #self.pool = {}
        self.connections = {}

    async def connect(self):
        assert config.local
        await dsc.client_connect(**config.local)

    def close(self):
        if dsc.client_agent:
            dsc.client_agent.close()
            dsc.client_agent = None
        self.pool = {}

    def __getattr__(self, name):
        if name not in self.pool:
            raise AttributeError
        return ServiceRef(name, self)

    async def request(self, srv, method, *params, conn_retry=0, retry=0):
        agent = dsc.client_agent
        assert agent
        if srv in self.pool:
            client = self.pool[srv]
        else:
            boxes = agent.route.get(srv)
            if not boxes:
                raise ConnectionError(
                    'no available rpc server')

            bad_boxes = []
            boxes = random.sample(boxes, len(boxes))

            # retry connect some times
            for _ in range(conn_retry + 1):
                if boxes:
                    box = boxes.pop()
                else:
                    box = random.choice(bad_boxes)

                logging.debug('got box %s for service %s', box, srv)
                client = WebSocketClient('ws://' + box)
                try:
                    await client.connect()
                    self.pool[srv] = client
                    break
                except OSError:
                    logging.error('cannot connect to %s', box)
                    bad_boxes.append(box)

            if srv not in self.pool:
                raise ConnectionError(
                    'all connection for service {} failed'.format(srv))
        try:
            return await client.request(srv, method, *params)
        except (ChannelClosed, ConnectionError):
            logging.error('channel closed')
            client.close()
            if srv in self.pool:
                del self.pool[srv]
            if retry <= 0:
                raise ConnectionError(
                    'cannot retry connections')
            
        return await self.request(srv, method,
                                  *params,
                                  conn_retry=conn_retry,
                                  retry=retry-1)
    
engine = MasterStandbyEngine()
