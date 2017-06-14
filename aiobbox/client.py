import logging
import asyncio
import random
import aiohttp
from aiochannel import Channel
from aiochannel.errors import ChannelClosed
from urllib.parse import urljoin
import json
import uuid
from aiobbox.cluster import get_cluster
from aiobbox.exceptions import ConnectionError, Retry
from aiobbox.utils import get_cert_ssl_context

try:
    import selectors
except ImportError:
    from asyncio import selectors

class HttpClient:
    def __init__(self, connect):
        c = get_cluster()
        box = c.boxes[connect]
        self.ssl_prefix = box['ssl']
        if self.ssl_prefix:
            self.url_prefix = 'https://' + connect
        else:
            self.url_prefix = 'http://' + connect
        ssl_context =get_cert_ssl_context(self.ssl_prefix)
        conn = aiohttp.TCPConnector(ssl_context=ssl_context)
        self.session = aiohttp.ClientSession(connector=conn)

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

    def __del__(self):
        self.session = None

class WebSocketClient:
    def __init__(self, connect):
        c = get_cluster()
        box = c.boxes[connect]
        self.ssl_prefix = box['ssl']
        if self.ssl_prefix:
            self.url_prefix = 'wss://' + connect
        else:
            self.url_prefix = 'ws://' + connect

        ssl_context = get_cert_ssl_context(self.ssl_prefix)
        conn = aiohttp.TCPConnector(ssl_context=ssl_context)
        self.session = aiohttp.ClientSession(connector=conn)
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

    async def request(self, srv, method, *params, req_id=None):
        if not self.connected:
            raise ConnectionError('websocket closed')

        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '::' + method
        if not req_id:
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
        self.session.close()
        self.waiters = {}

    async def connect_wait(self):
        while self.cont:
            if not self.ws:
                await self.connect()
            if not self.ws:
                await asyncio.sleep(1.0)
                continue
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
                return await self.onclosed()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logging.debug('error during received %s',
                              self.ws.exception() if self.ws else None)
                return await self.onclosed()
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logging.debug('websocket closed')
                return

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
        return await self.srv_ref.pool.request(
            self.srv_ref.name,
            self.name,
            *params,
            **self.kw)

class ServiceRef:
    def __init__(self, srv_name, pool):
        self.name = srv_name
        self.pool = pool

    def __getattr__(self, name):
        return MethodRef(name, self)

class FullConnectPool:
    FIRST = 1
    RANDOM = 2

    def __init__(self):
        self.pool = {}
        self.policy = self.FIRST
        self.max_concurrency = 10

    async def ensure_clients(self, srv):
        agent = get_cluster()
        boxes = agent.route[srv]

        # connect at most n concurrent connections
        for bind in sorted(boxes)[:self.max_concurrency]:
            if bind not in self.pool:
                # add box to pool
                box = agent.boxes[bind]
                client = WebSocketClient(
                    bind)
                self.pool[bind] = client

        for bind, client in list(self.pool.items()):
            if bind not in agent.boxes:
                logging.warning('remove box %s', bind)
                # remove box due to server done
                client.close()
                del self.pool[bind]

        for _ in range(30):
            c = self.get_client(srv, policy=self.FIRST)
            if c:
                return
            await asyncio.sleep(0.01)

    def get_client_count(self, srv):
        cc = get_cluster()
        cnt = 0
        for bind in cc.route[srv]:
            client = self.pool.get(bind)
            if client and client.connected:
                cnt += 1
        return cnt

    def get_client(self, srv, policy=None, boxid=None):
        policy = policy or self.policy
        clients = []
        cc = get_cluster()
        for bind in cc.route[srv]:
            client = self.pool.get(bind)
            if client and client.connected:
                if boxid:
                    box = cc.boxes.get(bind)
                    if box.boxid != boxid:
                        continue
                if policy == self.FIRST:
                    return client
                else:
                    assert policy == self.RANDOM
                    clients.append(client)
        if clients:
            return random.choice(clients)

    def __getattr__(self, name):
        return ServiceRef(name, self)

    async def request(self, srv, method, *params, boxid=None, retry=0, req_id=None):
        if not req_id:
            req_id = uuid.uuid4().hex
        for rty in range(retry + 1):
            try:
                return await self._request(srv, method,
                                           *params, boxid=None,
                                           req_id=req_id)
            except Retry:
                continue
        raise ConnectionError(
            'cannot retry connections')

    async def _request(self, srv, method, *params, boxid=None, req_id=None):
        await self.ensure_clients(srv)
        client = self.get_client(srv, boxid=boxid)
        if not client:
            raise ConnectionError(
                'no available rpc server')

        if not req_id:
            req_id = uuid.uuid4().hex
        try:
            return await client.request(srv, method, *params, req_id=req_id)
        except ConnectionError:
            assert not client.connected
            raise Retry()

pool = FullConnectPool()
