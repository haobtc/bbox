import sys
import os
import logging
import asyncio
from aiohttp import web
from aiobbox.server import Service, ServiceError
from aiobbox.client import pool
from aiobbox.exceptions import ConnectionError

# service
srv = Service()
@srv.method('wsdata')
def wsdata(request, data):
    pass
srv.register('gateway')

# webserver
async def handle_req(request):
    http_handler = os.getenv('RPC_BACKEND')
    if not http_handler:
        return web.HTTPNotFound()
    webreq = {
        'method': request.method,
        'path': request.path,
        'qs': request.query_string,
        'headers': dict(request.headers.items()),
        'body': None
        }

    if request.method in ('POST', 'PUT'):
        ctype = request.headers.get('Content-Type',
                                    'application/octet-stream')
        if ctype in ('application/x-www-form-urlencoded',
                     'application/json'):
            # ONLY parse known body
            body = await request.post()
            webreq['body'] = dict(body.items())

    srv, method = http_handler.split('::')
    try:
        r = await pool.request(srv, method, webreq)
    except ConnectionError:
        return web.HTTPBadGateway()
    if r['result']:
        res = r['result']
        if isinstance(res, str):
            return web.Response(body=res)
        elif 'body' in res:
            headers = res.get('headers', {})
            body = res['body']
            if isinstance(body, str):
                return web.Response(body=body, headers=headers)
            else:
                headers.pop('Content-Type', None)
                return web.json_response(body, headers=headers)
        else:
            return web.json_response(res)
    else:
        code = r['error'].get('code', '500')
        if code.isdigit():
            code = int(code)
        else:
            code = 500
        return web.Response(status=code,
                            body=r['error'].get('message', ''))

async def all_middleware(app, handler):
    return handle_req
            

async def start(handler=None, bind='127.0.0.1'):
    pass

async def shutdown():
    pass

async def get_app(bind='127.0.0.1:28080'):
    app = web.Application(middlewares=[all_middleware])
    return app
        
