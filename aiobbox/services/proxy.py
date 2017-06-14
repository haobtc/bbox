import sys
import re
import os
import logging
import asyncio
from aiohttp import web

from aiobbox.utils import parse_method
from aiobbox.client import pool
from aiobbox.exceptions import ConnectionError
from aiobbox.handler import BaseHandler

_whitelist = None
# proxy server
async def handle_rpc(request):
    body = await request.json()
    if ('method' not in body
        or not isinstance(body['method'], str)):
        return web.HTTPBadRequest()

    m = parse_method(body['method'])
    if not m:
        return web.HTTPBadRequest()

    if _whitelist is not None:
        if body['method'] not in _whitelist:
            return web.HTTPForbidden()
    
    # TODO: srv::method white list
    srv, method = m.group('srv'), m.group('method')
    
    params = body['params']
    try:
        r = await pool.request(srv, method,
                               *params,
                               req_id=body.get('id'))
    except ConnectionError:
        return web.HTTPBadGateway()
    return web.json_response(r)

class Handler(BaseHandler):
    async def get_app(self, args):
        app = web.Application()
        app.router.add_post('/jsonrpc/2.0/api', handle_rpc)
        #app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
        #app.router.add_get('/', index)
        return app

    def add_arguments(self, parser):
        parser.add_argument(
            '--whitelist',
            type=str,
            nargs='*',
            help='srv method white list')

    async def start(self, args):
        global _whitelist
        if args.whitelist:
            _whitelist = set(args.whitelist)


