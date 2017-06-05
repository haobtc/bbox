import sys
import logging
import asyncio
from aiohttp import web
from aiobbox.server import Service, ServiceError
from aiobbox.client import pool

# service
srv = Service()
@srv.method('wsdata')
def wsdata(request, data):
    pass
srv.register('httpd')


# webserver
http_handler = None
async def handle_req(request):
    if not http_handler:
        return web.HTTPNotFound()
    webreq = {
        'method': request.method,
        'path': request.path,
        'qs': request.query_string,
        'headers': dict(request.headers.items()),
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
    r = await pool.request(srv, method, webreq)
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
        code = int(r['error'].get('code', 500))
        return web.Response(status=code,
                            body=r['error'].get('message', ''))

async def all_middleware(app, handler):
    return handle_req
            
app_handler = None
async def http_server(handler=None, bind='127.0.0.1:28080'):
    global http_handler
    http_handler = handler
    app = web.Application(middlewares=[all_middleware])
    #resource = app.router.add_resource(r'/(.*)')
    #resource.add_route('*', handle_req)

    handler = app.make_handler()
    host, port = bind.split(':')
    logging.warn('httpd starts at %s', bind)
    loop = asyncio.get_event_loop()
    srv = await loop.create_server(handler, host, port)
    app_handler = handler

async def start(handler=None, bind='127.0.0.1'):
    return await http_server(handler=handler, bind=bind)

async def shutdown():
    if app_handler:
        await app_handler.finish_connections()

