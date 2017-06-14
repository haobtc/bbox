import re
import time
import logging
import os, json
import asyncio
import json
from aiohttp import web
from functools import wraps
from aiobbox.cluster import get_box, get_cluster
from aiobbox.exceptions import ServiceError
from aiobbox.utils import parse_method, get_ssl_context
from aiobbox.metrics import collect_metrics
from aiobbox import stats

DEBUG = True
srv_dict = {}

class MethodRef:
    def __init__(self, fn, private=False):
        self.fn = fn
        self.private = private

class Service(object):
    def __init__(self):
        self.methods = {}

    def register(self, srv_name):
        if srv_name in srv_dict:
            logging.warn('srv {} already exist'.format(srv_name))
        srv_dict[srv_name] = self

    def method(self, name, private=False):
        def decorator(fn):
            __w = wraps(fn)(fn)
            if name in self.methods:
                logging.warn('method {} already exist'.format(name))
            self.methods[name] = MethodRef(__w, private=private)
            return __w
        return decorator

class Request:
    def __init__(self, body):
        self.body = body
        self.req_id = None
        self.params = None
        self.srv = None

    async def handle(self):
        stats_name = None
        try:
            start_time = time.time()
            self.req_id = self.body.get('id')
            if (not isinstance(self.req_id, str) or
                self.req_id is None):
                raise ServiceError('invalpid reqid',
                                   '{}'.format(self.req_id))

            self.params = self.body.get('params', [])

            method = self.body['method']
            if not isinstance(method, str):
                raise ServiceError('invalid method',
                                   'method should be string')

            m = parse_method(method)
            if not m:
                raise ServiceError('invalid method',
                                   'Method should be ID::ID')

            srv_name = m.group('srv')
            self.method = m.group('method')
            self.srv = srv_dict.get(srv_name)
            if not self.srv:
                raise ServiceError(
                    'service not found',
                    'server {} not found'.format(srv_name))
            try:
                method_ref = self.srv.methods[self.method]
            except KeyError:
                raise ServiceError(
                    'method not found',
                    'Method {} does not exist'.format(self.method))
            stats_name = '/{}/{}'.format(srv_name, self.method)
            stats.rpc_request_count.incr(stats_name)
            res = await method_ref.fn(self, *self.params)
            resp = {'result': res,
                    'id': self.req_id,
                    'error': None}
            end_time = time.time()
            if end_time - start_time > 1.0:
                stats.slow_rpc_request_count.incr(stats_name)
        except ServiceError as e:
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
            if stats_name:
                stats.error_rpc_request_count.incr(stats_name)
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

async def handle_metrics_json(request):
    resp = await collect_metrics()
    box = get_box()
    for name, labels, v in resp['lines']:
        labels['box'] = box.boxid
    return web.json_response(resp)

async def handle_metrics(request):
    '''
    aggregate metrics of all nodes
    '''
    resp = await collect_metrics()
    lines = []

    for name, define in resp['meta'].items():
        lines.append('# HELP {} {}'.format(
            name, define['help']))
        lines.append('# TYPE {} {}'.format(
            name, define['type']))
    for name, labels, v in resp['lines']:
        d = ', '.join('{}="{}"'.format(lname, lvalue)
                      for lname, lvalue in labels.items())
        d = '{' + d + '}'
        lines.append('{} {} {}'.format(name, d, v))
    return web.Response(text='\n'.join(lines))

async def start_server(args):
    boxid = args.boxid

    ssl_context = get_ssl_context(args.ssl)

    # server etcd agent
    srv_names = list(srv_dict.keys())
    curr_box = get_box()
    curr_box.ssl_prefix = args.ssl
    await curr_box.start(boxid, srv_names)

    app = web.Application()
    app.router.add_post('/jsonrpc/2.0/api', handle)
    app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
    app.router.add_get('/metrics', handle_metrics)
    app.router.add_get('/metrics.json', handle_metrics_json)
    app.router.add_get('/', index)

    host, port = curr_box.bind.split(':')
    logging.warn('box {} launched as {}'.format(
        curr_box.boxid,
        curr_box.bind))
    handler = app.make_handler()
    loop = asyncio.get_event_loop()
    srv = await loop.create_server(handler,
                                   host, port,
                                   ssl=ssl_context)
    return srv, handler
