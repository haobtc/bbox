import sys
import re
import os
import logging
import asyncio
from aiohttp import web

from aiobbox.exceptions import ServiceError
from aiobbox.utils import parse_method
from aiobbox.client import pool
from aiobbox.exceptions import ConnectionError
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

_whitelist = None

# proxy server
async def handle_rpc(request):
    body = await request.json()
    if ('method' not in body
        or not isinstance(body['method'], str)):
        logger.warn('bad request for for body %s', body)
        return web.HTTPBadRequest()

    m = parse_method(body['method'])
    if not m:
        logger.warn('parse method error %s', body)
        return web.HTTPBadRequest()

    if _whitelist is not None:
        if body['method'] not in _whitelist:
            logger.warn('method not in whitelist')
            return web.HTTPForbidden()

    # TODO: srv::method white list
    srv, method = m.group('srv'), m.group('method')

    params = body['params']
    try:
        r = await pool.request(srv, method,
                               *params,
                               req_id=body.get('id'))
    except ConnectionError:
        logger.warn('connect error on request srv %s, method %s', srv, method)
        return web.HTTPBadGateway()
    return web.json_response(r)

async def handle_ws(request):
    ws = web.WebSocketResponse(autoping=True)
    await ws.prepare(request)

    async for req_msg in ws:
        body = json.loads(req_msg.data)
        asyncio.ensure_future(handle_ws_body(ws, body))

async def handle_ws_body(ws, body):
    try:
        if ('method' not in body
            or not isinstance(body['method'], str)):
            raise ServiceError('bad request')

        m = parse_method(body['method'])
        if not m:
            raise ServiceError('bad request')

        if _whitelist is not None:
            if body['method'] not in _whitelist:
                raise ServiceError('access denied')

        srv, method = m.group('srv'), m.group('method')

        params = body['params']
        try:
            r = await pool.request(srv, method,
                                   *params,
                                   req_id=body.get('id'))
            ws.send_json(r)
        except ConnectionError:
            raise ServiceError('connection failed')
    except ServiceError as e:
        error_info = {
            'message': getattr(e, 'message', str(e)),
            'code': e.code
        }
        ws.send_json({'error': error_info,
                      'id': self.req_id,
                      'result': None})

class Handler(BaseHandler):
    async def get_app(self, args):
        app = web.Application()
        app.router.add_post('/jsonrpc/2.0/api', handle_rpc)
        app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
        return app

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow', '-a',
            type=str,
            nargs='*',
            help='allowed srv::method')

    async def start(self, args):
        global _whitelist
        if args.allow:
            _whitelist = set(args.allow)
