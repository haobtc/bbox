import asyncio
import json
import aiohaorpc.server as haoserver
from aiohttp import web
from services import calc

class Request:
    def __init__(self, body):
        srv_name, self.method = body['method'].split('.')
        self.srv = haoserver.srv_dict[srv_name]
        self.params = body['params']
        self.req_id = body['id']

    async def handle(self):
        try:
            fn = self.srv.methods[self.method]
            res = await fn(self, *self.params)
            resp = {'result': res,
                    'id': self.req_id,
                    'error': None}
        except Exception as e:
            import traceback
            traceback.print_exc()
            resp = {'error': str(e.message),
                    'id': self.req_id,
                    'result': None}
        return resp

    async def handle_ws(self, ws):
        resp = await self.handle()
        ws.send_str(json.dumps(resp))
        return resp
        
        
async def handle(request):
    body = await request.json()
    req = Request(body)
    resp = await req.handle()
    return web.json_response(resp)

async def handle_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    async for req_msg in ws:
        print(req_msg)

        body = json.loads(req_msg.data)
        req = Request(body)
        asyncio.ensure_future(req.handle_ws(ws))


async def index(request):
    return web.Response(text='hello')

app = web.Application()

app.router.add_post('/jsonrpc/2.0/api', handle)
app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
app.router.add_get('/', index)

web.run_app(app)
    
