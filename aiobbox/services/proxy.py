import sys
import json
import re
import os
import logging
import asyncio
from aiohttp import web
from aiohttp import ClientConnectorError

from aiobbox.cluster import get_cluster
from aiobbox.exceptions import ServiceError
from aiobbox.jsonrpc import Request, DataError

from aiobbox.client import pool as srv_pool
from aiobbox.exceptions import ConnectionError, NoServiceFound
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

_whitelist = None

# proxy server
async def handle_rpc(request: web.Request) -> web.Response: # type: ignore
    body = await request.json()

    try:
        req = Request(body)
    except DataError as e:
        logger.warn('json parse error %s', body)
        return web.HTTPBadRequest(body='json parse error')

    if _whitelist is not None:
        if not req.allowed(_whitelist):
            logger.warn('method not allowed')
            return web.HTTPForbidden()

    try:
        timeout = float(
            request.headers.get('X-Bbox-Proxy-Timeout', '20'))
    except ValueError:
        timeout = 20

    try:
        r = await srv_pool.request_obj(
            req,
            timeout=timeout)
        return web.json_response(r)
    except asyncio.TimeoutError:
        logging.warn('timeout error on request %s', req.full_method, exc_info=True)
    except ClientConnectorError:
        logger.warn('client connector error, method %s', req.method, exc_info=True)
        await get_cluster().get_boxes()
    except ConnectionError:
        logger.warn('connect error on request %s', req.full_method, exc_info=True)
        await get_cluster().get_boxes()
    except NoServiceFound:
        logger.warn('no service found for %s', req.full_method)
        await get_cluster().get_boxes()
        return web.HTTPNotFound()

    return web.HTTPBadGateway()


class Handler(BaseHandler):
    async def get_app(self, args):
        app = web.Application()
        app.router.add_post('/jsonrpc/2.0/api', handle_rpc)
        return app

    def add_arguments(self, parser):
        parser.add_argument(
            '--allow', '-a',
            type=str,
            help='allowed list of srv::method separated by comma')

    async def start(self, args):
        global _whitelist
        if args.allow:
            _whitelist = set(args.allow.split(','))
