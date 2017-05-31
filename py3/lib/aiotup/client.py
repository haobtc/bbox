import aiohttp
import json
import websockets
import uuid
from urllib.parse import urljoin

class Client:
    def __init__(self, url_prefix='http://localhost:8080'):
        self.url_prefix = url_prefix

    async def request(self, srv, method, params):
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
        
    async def connect(self):
        url = self.url_prefix + '/jsonrpc/2.0/ws'
        self.ws = await websockets.connect(url)

    async def request(self, srv, method, params, coro=None):
        url = urljoin(self.url_prefix,
                      '/jsonrpc/2.0/api')

        method = srv + '.' + method
        req_id = uuid.uuid4().hex
        payload = {
            'id': req_id,
            'method': method,
            'params': params
            }
        return await self.send(payload, coro)

    async def send(self, body, coro=None):
        req_id = body.get('id')
        if req_id and coro:
            self.waiters[req_id] = coro
        return await self.ws.send(json.dumps(body))

    async def wait(self):
        while True:
            data = await self.ws.recv()
            data = json.loads(data)
            req_id = data.get('id')
            if req_id:
                coro = self.waiters.get(req_id)
                if coro:
                    #asyncio.ensure_future(core())
                    await coro(data)
    
        
            
