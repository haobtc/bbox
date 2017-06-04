import re
import logging
import os, json
import asyncio
import json
from aiohttp import web
from functools import wraps
from aiobbox.cluster import get_box, get_cluster

DEBUG = True

srv_dict = {}

class Service(object):
    def __init__(self, srv_name):
        self.srv_name = srv_name
        self.methods = {}
        if srv_name in srv_dict:
            logging.warn('srv {} already exist'.format(srv_name))
        srv_dict[srv_name] = self

    def method(self, name):
        def decorator(fn):
            __w = wraps(fn)(fn)
            if name in self.methods:
                logging.warn('method {} already exist'.format(name))
            self.methods[name] = __w
            return __w
        return decorator

class BboxError(Exception):
    def __init__(self, code, msg=None):
        self.code = code
        super(BboxError, self).__init__(msg or code)

class Request:
    def __init__(self, body):
        self.body = body
        self.req_id = None
        self.params = None
        self.srv = None
        
    async def handle(self):
        try:
            self.req_id = self.body.get('id')
            if (not isinstance(self.req_id, str) or
                self.req_id is None):
                raise BboxError('invalpid reqid',
                               '{}'.format(self.req_id))
            
            self.params = self.body.get('params', [])

            method = self.body['method']
            if not isinstance(method, str):
                raise BboxError('invalid method',
                               'method should be string')
            
            m = re.match(r'(\w[\.\w]*)::(\w+)$', method)
            if not m:
                raise BboxError('invalid method',
                               'Method should be ID::ID')

            srv_name = m.group(1)
            self.method = m.group(2)
            self.srv = srv_dict.get(srv_name)
            if not self.srv:
                raise BboxError(
                    'service not found',
                    'server {} not found'.format(srv_name))
            try:
                fn = self.srv.methods[self.method]
            except KeyError:
                raise BboxError('method not found',
                               'Method {} does not exist'.format(self.method))

            res = await fn(self, *self.params)
            resp = {'result': res,
                    'id': self.req_id,
                    'error': None}
        except BboxError as e:
            error_info = {
                'message': getattr(e, 'message', str(e)),
                'code': e.code
            }
            resp = {'error': error_info,
                    'id': self.req_id,
                    'result': None}
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_info = {
                'message': getattr(e, 'message', str(e)),
                }
            code = getattr(e, 'code', None)
            if code:
                error_info['code'] = code
            if DEBUG:
                error_info['stack'] = traceback.format_exc()
            resp = {'error': error_info,
                    'id': self.req_id,
                    'result': None}
        return resp

    async def handle_ws(self, ws):
        resp = await self.handle()
        if resp:
            ws.send_json(resp)
        return resp
        
async def handle(request):
    body = await request.json()
    req = Request(body)
    resp = await req.handle()
    return web.json_response(resp)

async def handle_ws(request):
    ws = web.WebSocketResponse(autoping=True)
    await ws.prepare(request)
    
    async for req_msg in ws:
        body = json.loads(req_msg.data)
        req = Request(body)
        asyncio.ensure_future(req.handle_ws(ws))

async def index(request):
    return web.Response(text='hello')

async def http_server(boxid, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    # client etcd agent
    await get_cluster().start()
    
    # server etcd agent
    srv_namess = list(srv_dict.keys())
    curr_box = get_box()
    await curr_box.start(boxid, srv_names)
    
    app = web.Application()
    app.router.add_post('/jsonrpc/2.0/api', handle)
    app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
    app.router.add_get('/', index)

    host, port = curr_box.bind.split(':')
    logging.info('box registered as {}'.format(curr_box.bind))
    print('box registered as {}'.format(curr_box.bind))    
    handler = app.make_handler()
    srv = await loop.create_server(handler, host, port)
    return srv, handler
