import sys
import json
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
        r = await pool.request(
            srv, method,
            *params,
            req_id=body.get('id'),
            timeout=8)
    except asyncio.TimeoutError:
        logging.warn('timeout error on request srv %s, method %s', srv, method, exc_info=True)
        return web.HTTPBadGateway()
    except ConnectionError:
        logger.warn('connect error on request srv %s, method %s', srv, method, exc_info=True)
        return web.HTTPBadGateway()
    return web.json_response(r)

class Handler(BaseHandler):
    async def get_app(self, args):
        app = web.Application()
        app.router.add_post('/jsonrpc/2.0/api', handle_rpc)
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
