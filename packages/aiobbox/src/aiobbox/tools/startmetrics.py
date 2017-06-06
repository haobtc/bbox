import os, sys
import logging
import uuid
import json
import asyncio
from aiohttp import web, ClientSession
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module

parser = argparse.ArgumentParser(
    prog='bbox metrics',
    description='start bbox python project')

parser.add_argument(
    '--bind',
    type=str,
    default='127.0.0.1:28081',
    help='the box service module to load')

async def get_box_metrics(bind, session):
    try:
        resp = await session.get('http://' + bind + '/metrics')
    except aiohttp.ClientConnectionError:
        logging.error('client connection error')
        return []
    return await resp.text()
    
async def handle_metrics(request):
    c = get_cluster()

    with ClientSession() as session:
        fns = [get_box_metrics(bind, session)
               for bind in c.boxes.keys()]
        if fns:
            res = await asyncio.gather(*fns)
        else:
            res = []
    header = [
        '# HELP rpc_request_count total number of rpc request since box start',
        '# TYPE rpc_request_count counter'
        ]
    headers = {'Content-Type': 'text/plain'}
    return web.Response(text='\n'.join(header + res), headers=headers)

async def http_server(bind='127.0.0.1:28081'):
    app = web.Application()
    app.router.add_get('/metrics', handle_metrics)
    app.router.add_get('/', handle_metrics)    

    handler = app.make_handler()
    host, port = bind.split(':')
    logging.warn('metrics starts at %s', bind)
    loop = asyncio.get_event_loop()
    srv = await loop.create_server(handler, host, port)
    return handler

httpd_mod = None
async def main():
    args = parser.parse_args()

    # start cluster client
    await get_cluster().start()
        
    handler = await http_server(bind=args.bind)
    return handler

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(handler.finish_connections())
