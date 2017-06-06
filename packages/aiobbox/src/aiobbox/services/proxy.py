import sys
import re
import os
import logging
import asyncio
from aiohttp import web

from aiobbox.client import pool
from aiobbox.exceptions import ConnectionError

# proxy server
async def handle_rpc(request):
    body = await request.json()
    if ('method' not in body
        or not isinstance(body['method'], str)):
        return web.HTTPBadRequest()
    
    m = re.match(r'(?P<srv>\w[\.\w]*)::(?P<method>\w+)$',
                 body['method'])
    if not m:
        return web.HTTPBadRequest()
    
    # TODO: srv::method white list
    srv, method = m.group('srv'), m.group('method')
    params = body['params']
    try:
        r = await pool.request(srv, method, *params, req_id=body.get('id'))
    except ConnectionError:
        return web.HTTPBadGateway()
    return web.json_response(r)

async def get_app(bind='127.0.0.1:28080'):
    app = web.Application()
    app.router.add_post('/jsonrpc/2.0/api', handle_rpc)
    #app.router.add_route('*', '/jsonrpc/2.0/ws', handle_ws)
    #app.router.add_get('/', index)
    return app
        
