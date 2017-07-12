import logging
import asyncio
import random
import aiohttp
from aiochannel import Channel
from aiochannel.errors import ChannelClosed
from urllib.parse import urljoin
import json
import uuid
from aiobbox.exceptions import ConnectionError, Retry

logger = logging.getLogger('bboxremote')

try:
    import selectors
except ImportError:
    from asyncio import selectors

class HttpClient:
    def __init__(self, url_prefix):
        self.url_prefix = url_prefix
        conn = aiohttp.TCPConnector()
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
        async with self.session.post(
                url, json=payload, timeout=10) as resp:
            ret = await resp.json()
            return ret

    def __del__(self):
        self.session = None

class WebSocketClient:
    def __init__(self, url_prefix):
        self.url_prefix = url_prefix
        conn = aiohttp.TCPConnector()
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
            logger.debug('connect to %s already connected',
                          self.url_prefix)
            return

        url = self.url_prefix + '/jsonrpc/2.0/ws'
        try:
            ws = await self.session.ws_connect(url, autoclose=False, autoping=False, heartbeat=1.0)
            self.ws = ws
        except OSError:
            logger.warn('connect to %s failed', url)

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
                logger.debug('error during received %s',
                              self.ws.exception() if self.ws else None)
                return await self.onclosed()
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                logger.debug('websocket closed')
                return

            req_id = data.get('id')
            if req_id:
                channel = self.waiters.get(req_id)
                if channel:
                    del self.waiters[req_id]
                    await channel.put(data)
                else:
                    logger.warn('Cannot find channel by id ', req_id)
            else:
                logger.debug('no reqid seems a notify', data)

class MethodRef:
    def __init__(self, name, srv_ref):
        self.name = name
        self.srv_ref = srv_ref

    async def __call__(self, *params, **kw):
        return await self.srv_ref.client.conn.request(
            self.srv_ref.name,
            self.name,
            *params)

class ServiceRef:
    def __init__(self, srv_name, client):
        self.name = srv_name
        self.client = client

    def __getattr__(self, name):
        return MethodRef(name, self)
                
class Client:
    def __init__(self, url_prefix):
        if url_prefix.startswith('http'):
            self.conn = HttpClient(url_prefix)
        else:
            assert url_prefix.startswith('ws')
            self.conn = WebSocketClient(url_prefix)

    def __getattr__(self, name):
        return ServiceRef(name, self)

    def __getitem__(self, name):
        return ServiceRef(name, self)
            
