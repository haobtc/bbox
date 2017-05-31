import logging
import asyncio
import aiohttp
from aiochannel import Channel
import json
import websockets
import uuid
from urllib.parse import urljoin

class Client:
    def __init__(self, url_prefix='http://localhost:8080'):
        self.url_prefix = url_prefix

    async def request(self, srv, method, *params):
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '.' + method
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
        
    async def connect(self):
        if self.ws:
            print('already connected')
            return
        url = self.url_prefix + '/jsonrpc/2.0/ws'
        self.ws = await websockets.connect(url)
        asyncio.ensure_future(self.wait())

    async def request(self, srv, method, *params):
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '.' + method
        req_id = uuid.uuid4().hex
        payload = {
            'id': req_id,
            'method': method,
            'params': params
            }

        channel = Channel(1)        
        self.waiters[req_id] = channel
        await self.ws.send(json.dumps(payload))
        return await channel.get()

    async def wait(self):
        while True:
            data = await self.ws.recv()
            data = json.loads(data)
            req_id = data.get('id')
            print('got data', data)
            if req_id:
                channel = self.waiters.get(req_id)
                if channel:
                    await channel.put(data)
                    del self.waiters[req_id]
                else:
                    logging.warn('Cannot find channel by id ', req_id)
            else:
                logging.debug('no reqid seems a notify', data)
